"""SDE-10: per-teacher call-count rate limit on AI-assisted block rewrite.

A call-count cap, not a dollar-cost cap (that remains `ops-observability/004`'s
separate, out-of-scope job). Same in-memory sliding-window shape as
`services.gateway.routers.webhooks`'s `WebhookProcessingState` + `_allow_request`
and `services.gateway.teaching_session.join`'s `JoinRateLimitState` +
`allow_join_attempt` -- just keyed by teacher id instead of webhook source /
(ip, room_code).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from datetime import datetime


class SlideDeckAiRewriteRateLimitConfig(BaseSettings):
    """Env prefix: SLIDE_DECK_AI_REWRITE_. Mirrors `webhooks/config.py`'s shape."""

    model_config = SettingsConfigDict(
        env_prefix="SLIDE_DECK_AI_REWRITE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    rate_limit_count: int = 20
    rate_limit_window_seconds: int = 3600  # 1 hour


def slide_deck_ai_rewrite_rate_limit_config() -> SlideDeckAiRewriteRateLimitConfig:
    # ponytail: uncached, same reasoning as auth/config.py's jwt_config().
    return SlideDeckAiRewriteRateLimitConfig()


@dataclass(slots=True)
class SlideDeckAiRewriteRateLimitState:
    """In-memory sliding-window state, one instance per gateway process.

    Mirrors `services.gateway.routers.webhooks.WebhookProcessingState`.
    ponytail: process-local, same ceiling as the webhook/join limiters this
    mirrors -- move to a shared store (e.g. Redis) if the gateway ever runs
    multiple processes and cross-process enforcement starts to matter.
    """

    request_times_by_teacher: dict[str, list[datetime]] = field(default_factory=dict)


def allow_ai_rewrite_attempt(
    state: SlideDeckAiRewriteRateLimitState,
    *,
    teacher_id: str,
    now: datetime,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> bool:
    """Sliding-window rate limit on AI-rewrite calls, keyed by teacher id.

    Same algorithm as `webhooks.py::_allow_request` / `join.py::allow_join_attempt`:
    count recent hits in a trailing window, evict stale ones, deny once at capacity.
    """
    config = slide_deck_ai_rewrite_rate_limit_config()
    if window_seconds is None:
        window_seconds = config.rate_limit_window_seconds
    window = timedelta(seconds=window_seconds)
    cap = limit if limit is not None else config.rate_limit_count
    recent = [
        seen_at for seen_at in state.request_times_by_teacher.get(teacher_id, []) if now - seen_at <= window
    ]
    if len(recent) >= cap:
        state.request_times_by_teacher[teacher_id] = recent
        return False
    recent.append(now)
    state.request_times_by_teacher[teacher_id] = recent
    return True


if __name__ == "__main__":
    # ponytail: smallest runnable check for the sliding-window algorithm,
    # no gateway app/DB needed.
    from datetime import UTC, datetime as dt

    state = SlideDeckAiRewriteRateLimitState()
    t0 = dt.now(UTC)
    assert all(
        allow_ai_rewrite_attempt(state, teacher_id="t1", now=t0, limit=3, window_seconds=60)
        for _ in range(3)
    )
    assert allow_ai_rewrite_attempt(state, teacher_id="t1", now=t0, limit=3, window_seconds=60) is False
    # a different teacher is an independent bucket
    assert allow_ai_rewrite_attempt(state, teacher_id="t2", now=t0, limit=3, window_seconds=60) is True
    # once the window has fully elapsed, the same teacher is allowed again
    later = t0 + timedelta(seconds=61)
    assert allow_ai_rewrite_attempt(state, teacher_id="t1", now=later, limit=3, window_seconds=60) is True
    print("slide_deck_ai_rewrite_rate_limit self-check OK")
