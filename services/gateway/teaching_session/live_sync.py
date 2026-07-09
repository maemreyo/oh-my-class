"""Redis Pub/Sub transport + Redis-hot session state (TSP-03 amendment).

Reuses the same Redis server already running in this stack for LiteLLM's
cache (`infra/compose/docker-compose.yml`'s `redis` service / the `REDIS_URL`
env var already passed to the gateway container) -- this module is the
gateway's *first* Redis client, added because none existed
(`packages/agents/healing/redis_breaker_store.py` hand-rolls the RESP
protocol over a raw socket; that is the anti-pattern this ADR-032 amendment
explicitly warns not to repeat, not a client to reuse). `redis` (redis-py)
is the standard, already-async-capable client -- added as a dependency
instead of hand-rolling Pub/Sub parsing.

Every function here is best-effort and never raises: Redis being down
degrades live broadcast only. The Postgres event log
(`teaching_session/event_log.py`) is the source of truth and is written
*before* any function in this module is called -- see
`event_log.record_event`'s docstring and every router in
`routers/teaching_session_live.py` for the "commit, then broadcast" order
that makes this safe.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import TYPE_CHECKING

import orjson
import redis.asyncio as redis

from services.gateway.teaching_session.events import SessionEvent, SessionReadModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_CHANNEL_PREFIX = "teaching_session:"
_STATE_KEY_PREFIX = "teaching_session:state:"
# ponytail: long enough to outlive a class period plus recess; a session
# that goes fully idle for this long just falls back to Postgres replay
# recovery on the next action, which is correct, just a bit slower.
_STATE_TTL_SECONDS = 6 * 3600

_client: redis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def session_channel(session_id: str) -> str:
    return f"{_CHANNEL_PREFIX}{session_id}"


def _state_key(session_id: str) -> str:
    return f"{_STATE_KEY_PREFIX}{session_id}"


def resolve_redis_url() -> str:
    """Build a real Redis URL from env, same host/port/auth as docker-compose.

    `.env`'s `REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}` relies on
    shell-style interpolation docker-compose performs but a plain Python
    process reading `.env` directly does not (same issue
    `packages/agents/healing/circuit_breaker.py::_resolve_redis_url`
    documents) -- and neither carries the `REDIS_AUTH` password. Building
    from the individual `REDIS_HOST`/`REDIS_PORT`/`REDIS_AUTH` parts avoids
    both problems without adding a second env convention.
    """
    url = os.environ.get("REDIS_URL", "")
    if url and "${" not in url:
        return url
    host = os.environ.get("REDIS_HOST", "localhost")
    port = os.environ.get("REDIS_PORT", "6379")
    auth = os.environ.get("REDIS_AUTH", "")
    auth_part = f":{auth}@" if auth else ""
    return f"redis://{auth_part}{host}:{port}"


def get_redis_client() -> redis.Redis:
    """Process-wide lazy singleton -- one connection pool, reused by every caller.

    Recreated automatically if the *running* event loop has changed since the
    client was created (asyncio connections are pinned to the loop that
    opened them) -- a real uvicorn worker never swaps its loop mid-process,
    so this branch never fires in production; it only matters for a test
    suite where each test function gets its own loop (this repo's
    `asyncio_mode = "auto"`), which would otherwise raise "Future attached
    to a different loop" the moment a second test touches Redis.
    """
    global _client, _client_loop
    current_loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not current_loop:
        _client = redis.Redis.from_url(resolve_redis_url(), decode_responses=True)
        _client_loop = current_loop
    return _client


async def publish_event(event: SessionEvent, client: redis.Redis | None = None) -> bool:
    """Best-effort publish to `session_channel(event.session_id)`. Returns success."""
    client = client or get_redis_client()
    try:
        data = orjson.dumps(event.model_dump(mode="json"))
        await client.publish(session_channel(event.session_id), data)
    except (redis.RedisError, OSError):
        return False
    return True


async def get_hot_state(
    session_id: str, client: redis.Redis | None = None,
) -> SessionReadModel | None:
    """`None` means "cold" -- Redis is unreachable or has no state for this session yet."""
    client = client or get_redis_client()
    try:
        raw = await client.get(_state_key(session_id))
    except (redis.RedisError, OSError):
        return None
    if raw is None:
        return None
    # decode_responses=True (both here and in get_redis_client()) means this is
    # always `str` at runtime -- the redis-py stubs type `.get()` as `bytes |
    # str` regardless, since the client is configurable either way.
    text = raw.decode() if isinstance(raw, bytes) else raw
    return _read_model_from_json(session_id, text)


async def set_hot_state(state: SessionReadModel, client: redis.Redis | None = None) -> bool:
    """Best-effort write-through of the derived state. Returns success."""
    client = client or get_redis_client()
    try:
        await client.set(
            _state_key(state.session_id), _read_model_to_json(state), ex=_STATE_TTL_SECONDS,
        )
    except (redis.RedisError, OSError):
        return False
    return True


async def subscribe(
    session_id: str, client: redis.Redis | None = None,
) -> AsyncIterator[SessionEvent]:
    """Yield live events published to `session_id`'s channel.

    Raises `redis.RedisError`/`OSError` immediately (subscribe) or mid-stream
    (listen) if Redis is unreachable -- callers (the SSE route) catch this to
    degrade to Postgres polling, matching the "polling fallback" sync
    transport policy.
    """
    client = client or get_redis_client()
    pubsub = client.pubsub()
    channel = session_channel(session_id)
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield SessionEvent.model_validate(orjson.loads(message["data"]))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


def _read_model_to_json(state: SessionReadModel) -> str:
    return orjson.dumps({
        "session_id": state.session_id,
        "current_slide_id": state.current_slide_id,
        "current_branch_id": state.current_branch_id,
        "open_interaction_id": state.open_interaction_id,
        "tallies": state.tallies,
        "ended": state.ended,
        "last_sequence": state.last_sequence,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }).decode()


def _read_model_from_json(session_id: str, raw: str) -> SessionReadModel:
    data = orjson.loads(raw)
    updated_at = data.get("updated_at")
    return SessionReadModel(
        session_id=session_id,
        current_slide_id=data.get("current_slide_id"),
        current_branch_id=data.get("current_branch_id"),
        open_interaction_id=data.get("open_interaction_id"),
        tallies=data.get("tallies") or {},
        ended=data.get("ended", False),
        last_sequence=data.get("last_sequence", 0),
        updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
    )
