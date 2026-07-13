"""Redis-backed rate limiting + abuse-throttling primitives (SEC-01).

Shared across gateway instances via the same Redis server the gateway
already depends on for `teaching_session/live_sync.py` (ADR-032) -- this
module reuses that connection resolution/client instead of standing up a
second one, so counters are fleet-wide (OPS-06), not per-process.

Two independent mechanisms live here:

* ``check_rate_limit`` -- a fixed-window counter (INCR + EXPIRE NX). Simple
  and atomic with two Redis calls; the tradeoff is a burst can double up
  right at a window boundary (e.g. a client could send ``limit`` requests at
  23:59:59 and another ``limit`` at 00:00:00). A sliding-log (ZSET per
  request timestamp) removes that boundary case but costs a Lua script /
  multi-key transaction for what is, at this scale, a cosmetic edge case.
  # ponytail: fixed window, not a true sliding log; upgrade to a ZSET-based
  # sliding window if boundary bursts are ever measured to matter.
* ``record_violation`` -- an escalating block: every time a caller trips a
  rate limit (or fails auth), a violation counter increments; once it
  crosses a threshold the caller is blocked outright for a duration that
  doubles each time, independent of the steady-state window above.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import orjson
import redis.asyncio as redis
from fastapi import HTTPException, status

from services.gateway.logging_config import get_logger
from services.gateway.teaching_session.live_sync import get_redis_client

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import JsonObject

_logger = get_logger("services.gateway.rate_limiting")

# Input-size ceilings for the create-run path (SEC-01): chosen to comfortably
# fit a real diagnose-then-generate request (a teacher's free-text brief plus
# class/student context) while bounding worst-case cost before the payload
# reaches the pipeline. Override via env if real traffic proves these wrong.
MAX_RAW_REQUEST_CHARS = int(os.getenv("OMC_MAX_RAW_REQUEST_CHARS", "20000"))
MAX_CLASS_INFO_BYTES = int(os.getenv("OMC_MAX_CLASS_INFO_BYTES", "50000"))

_RATE_PREFIX = "ratelimit:"
_VIOLATION_PREFIX = "ratelimit:violations:"
_BLOCK_PREFIX = "ratelimit:blocked:"

# Escalating block durations (seconds), indexed by violation count once the
# threshold below is crossed. Caps at the last entry for repeat offenders.
_ABUSE_THRESHOLD = 5
_VIOLATION_WINDOW_SECONDS = 600  # 10 minutes: violations older than this don't count
_ESCALATION_SECONDS = (60, 300, 900, 3600)  # 1m, 5m, 15m, 1h (repeat offenders stay at 1h)


@dataclass(frozen=True, slots=True)
class RateLimitTier:
    """A named request budget: at most ``limit`` requests per ``window_seconds``."""

    limit: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitOutcome:
    allowed: bool
    remaining: int
    retry_after_seconds: int


def rate_limit_redis_client() -> redis.Redis:
    """Shared Redis client -- same singleton `live_sync` already maintains."""
    return get_redis_client()


def enforce_payload_size_limits(raw_request: str, class_info: JsonObject) -> None:
    """Reject oversized `raw_request`/`class_info` (incl. nested `student_evidence`)
    before they reach the pipeline. Raises HTTPException(413) if either is too large.
    """
    if len(raw_request) > MAX_RAW_REQUEST_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"raw_request exceeds {MAX_RAW_REQUEST_CHARS} characters",
        )
    class_info_bytes = len(orjson.dumps(class_info))
    if class_info_bytes > MAX_CLASS_INFO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"class_info exceeds {MAX_CLASS_INFO_BYTES} bytes",
        )


async def check_rate_limit(
    client: redis.Redis,
    key: str,
    tier: RateLimitTier,
    *,
    now: float | None = None,
) -> RateLimitOutcome:
    """Fixed-window counter check. Increments unconditionally (each check costs one request)."""
    now = time.time() if now is None else now
    window_index = int(now // tier.window_seconds)
    redis_key = f"{_RATE_PREFIX}{key}:{window_index}"

    count = await client.incr(redis_key)
    if count == 1:
        await client.expire(redis_key, tier.window_seconds)

    retry_after = tier.window_seconds - int(now % tier.window_seconds)
    if count > tier.limit:
        return RateLimitOutcome(allowed=False, remaining=0, retry_after_seconds=retry_after)
    return RateLimitOutcome(
        allowed=True, remaining=tier.limit - count, retry_after_seconds=retry_after
    )


async def is_blocked(client: redis.Redis, principal_key: str) -> int | None:
    """Return remaining block seconds, or None if not currently blocked."""
    ttl = await client.ttl(f"{_BLOCK_PREFIX}{principal_key}")
    return ttl if ttl and ttl > 0 else None


async def record_violation(client: redis.Redis, principal_key: str, *, reason: str) -> int | None:
    """Record a rate-limit/auth-failure violation; escalate to a hard block past threshold.

    Returns the new block duration in seconds if this violation just triggered
    (or extended) a block, else None.
    """
    violation_key = f"{_VIOLATION_PREFIX}{principal_key}"
    count = await client.incr(violation_key)
    if count == 1:
        await client.expire(violation_key, _VIOLATION_WINDOW_SECONDS)

    if count < _ABUSE_THRESHOLD:
        return None

    escalation_index = min(count - _ABUSE_THRESHOLD, len(_ESCALATION_SECONDS) - 1)
    block_seconds = _ESCALATION_SECONDS[escalation_index]
    await client.set(f"{_BLOCK_PREFIX}{principal_key}", "1", ex=block_seconds)

    # Structured log line -- the metric OPS-04 alerting watches for sustained
    # 429/abuse spikes. No dedicated metrics pipeline exists yet in this
    # service (see logging_config's structlog/stdlib-JSON split); this is the
    # observability surface that already exists and that a log-based alert
    # rule can watch for `event="rate_limit.abuse_blocked"`.
    _logger.warning(
        "rate_limit.abuse_blocked principal=%s reason=%s violations=%d block_seconds=%d",
        principal_key,
        reason,
        count,
        block_seconds,
    )
    return block_seconds
