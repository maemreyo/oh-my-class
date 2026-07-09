from __future__ import annotations

from uuid import uuid4

import anyio
import pytest
import redis.asyncio as redis

from services.gateway.teaching_session import live_sync
from services.gateway.teaching_session.events import (
    SessionEventType,
    SessionReadModel,
    build_event,
    initial_read_model,
)
from services.gateway.teaching_session.tokens import SessionRole

# Mirrors test_teaching_session_event_log.py's hardcoded DATABASE_URL pattern:
# a real dev Redis is already running (docker-compose's `redis` service), but
# `live_sync.get_redis_client()`'s env-based URL resolution needs REDIS_AUTH
# in the shell env, which a bare `pytest` invocation doesn't load from `.env`.
# Hardcode the same default credential docker-compose falls back to instead.
TEST_REDIS_URL = "redis://:omc_redis_secret@localhost:6379"


def _test_client() -> redis.Redis:
    return redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)


async def _skip_if_unreachable(client: redis.Redis) -> None:
    try:
        await client.ping()
    except (redis.RedisError, OSError):
        pytest.skip("Redis is not reachable in this environment")


class BrokenRedisClient:
    """Every call raises a connection error -- simulates Redis being down."""

    async def publish(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")

    async def get(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")

    async def set(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")

    def pubsub(self) -> BrokenPubSubClient:
        return BrokenPubSubClient()


class BrokenPubSubClient:
    async def subscribe(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")


class TestDegradesWhenRedisIsDown:
    """AC (amendment): Redis being unreachable never raises out of these
    functions -- live broadcast/hot-state pauses, it never breaks the caller."""

    async def test_publish_event_returns_false_instead_of_raising(self) -> None:
        broken = BrokenRedisClient()
        event = build_event(
            session_id="s1", event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1"},
        )
        ok = await live_sync.publish_event(event, client=broken)  # type: ignore[arg-type]
        assert ok is False

    async def test_get_hot_state_returns_none_instead_of_raising(self) -> None:
        broken = BrokenRedisClient()
        state = await live_sync.get_hot_state("s1", client=broken)  # type: ignore[arg-type]
        assert state is None

    async def test_set_hot_state_returns_false_instead_of_raising(self) -> None:
        broken = BrokenRedisClient()
        ok = await live_sync.set_hot_state(initial_read_model("s1"), client=broken)  # type: ignore[arg-type]
        assert ok is False

    async def test_subscribe_raises_on_first_iteration_for_callers_to_catch(self) -> None:
        """`subscribe` itself is allowed to raise (unlike the others) -- the SSE
        route (`routers/teaching_session_live.py::_sse_relay`) is the one that
        catches it and degrades to polling; a raw generator that silently
        yielded nothing would be indistinguishable from "no events yet"."""
        broken = BrokenRedisClient()
        with pytest.raises(redis.RedisError):
            async for _event in live_sync.subscribe("s1", client=broken):  # type: ignore[arg-type]
                pass


class TestLiveRedisRoundTrip:
    """Exercises the real dev Redis (skips if unreachable) -- the actual
    Pub/Sub + hot-state mechanism, not just the degradation path above."""

    async def test_set_then_get_hot_state_round_trips(self) -> None:
        client = _test_client()
        await _skip_if_unreachable(client)

        session_id = f"live-sync-{uuid4()}"
        state = SessionReadModel(session_id=session_id, current_slide_id="slide-9", last_sequence=3)
        ok = await live_sync.set_hot_state(state, client=client)
        assert ok is True

        recovered = await live_sync.get_hot_state(session_id, client=client)
        assert recovered is not None
        assert recovered.current_slide_id == "slide-9"
        assert recovered.last_sequence == 3

    async def test_publish_is_received_by_a_subscriber(self) -> None:
        client = _test_client()
        await _skip_if_unreachable(client)

        session_id = f"live-sync-{uuid4()}"
        event = build_event(
            session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "slide-live"},
        ).model_copy(update={"sequence": 1})

        received: list[object] = []

        async def _subscribe_and_collect() -> None:
            async for received_event in live_sync.subscribe(session_id, client=client):
                received.append(received_event)
                return

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(_subscribe_and_collect)
            await anyio.sleep(0.2)  # let the subscription establish before publishing
            await live_sync.publish_event(event, client=client)
            with anyio.move_on_after(2.0):
                while not received:
                    await anyio.sleep(0.05)

        assert len(received) == 1
        assert received[0].payload == {"slide_id": "slide-live", "slide_index": None}
