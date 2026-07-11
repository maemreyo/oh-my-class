"""ADR-032 live-path-proof for TSP-03: the Redis-backed event log/Pub-Sub
mechanism (`teaching_session/event_log.py`, `teaching_session/live_sync.py`)
is invoked through the real, registered FastAPI route + dependency chain
(session-role-token auth, real Postgres, real Redis) -- not merely exercised
by a unit test calling `record_event`/`publish_event` directly. That gap --
a Redis-backed module with zero runtime callers -- is exactly what made
`packages/agents/healing/redis_breaker_store.py` dead code per the 2026-07-01
audit; these tests hit the actual `services.gateway.routers.
teaching_session_live.router` object (the one `main.py` includes at
`/teaching-sessions`), the same way `test_teaching_pack_stream_router.py`
proves its own SSE route.
"""

from __future__ import annotations

import os
from functools import partial
from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.models import Role, User
from services.gateway.models import Base
from services.gateway.routers.teaching_session_live import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.teaching_session import live_sync, service
from services.gateway.teaching_session.models import (
    RetentionTier,
    TeachingSession,
    TeachingSessionEvent,
)
from services.gateway.teaching_session.responses import SessionResponseAggregate
from services.gateway.teaching_session.tokens import SessionRole, mint_session_token
from services.gateway.tests.teaching_pack_preview_helpers import delete_run

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

# `live_sync.get_redis_client()` is a process-wide singleton that resolves its
# URL from REDIS_URL (or REDIS_HOST/REDIS_PORT/REDIS_AUTH) at first call --
# see live_sync.py's docstring. `uv run` auto-loads this repo's `.env`, whose
# `REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}` gets interpolated against
# `.env`'s own `REDIS_HOST=redis` (the docker-compose *service* name, only
# resolvable from inside the docker network) -- so `REDIS_URL` is already
# set to a host-unreachable value by the time this module runs, and
# `setdefault` would leave it alone. Force an override (not setdefault) so
# the app's own in-route Redis calls resolve to the real dev Redis published
# on localhost -- same root cause `test_teaching_session_live_sync.py`
# works around with its own hardcoded `TEST_REDIS_URL` constant.
os.environ["REDIS_URL"] = "redis://:omc_redis_secret@localhost:6379"

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER = User(user_id="teacher-live-router", username="teacher-live-router", role=Role.TEACHER)


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/teaching-sessions")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda c: set(Base.metadata.tables))
        if "public.teaching_session_events" not in existing_tables:
            pytest.skip("teaching_session_events table is not present — run alembic upgrade head")
    await engine.dispose()


async def _create_session(
    *,
    retention_tier: RetentionTier = RetentionTier.AGGREGATE,
    class_id: str | None = None,
    deck_id: str = "deck-1",
    snapshot_id: str = "snap-1",
) -> TeachingSession:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        created = await service.create_session(
            db,
            session_id=f"live-{uuid4()}",
            teacher_id=OWNER.user_id,
            deck_id=deck_id,
            snapshot_id=snapshot_id,
            retention_tier=retention_tier,
            class_id=class_id,
        )
        await db.commit()
    await engine.dispose()
    return created


async def _seed_slide_deck_snapshot(run_id: RunId, *, student_html: str) -> str:
    """A real `ArtifactSnapshot` row for `GET /{session_id}/content` to fetch --
    `TeachingSession.snapshot_id` has no DB-level FK to `artifact_snapshots`
    (plain string column), so a content-endpoint test needs its own row."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await TeachingPackRunStore(db).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId(OWNER.user_id),
            raw_request="Test teaching session content route",
            class_info={"grade": 5},
        ))
        snapshot = await TeachingPackSnapshotStore(db).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="deck-1",
            artifact_type="slide_deck",
            content_json={"deck_id": "deck-1", "teacher_only": {"secret_notes": "top-secret"}},
            rendered_html="<!DOCTYPE html><html><body>teacher-only-view</body></html>",
            student_rendered_html=student_html,
            renderer_version="1.0",
        ))
        await db.commit()
        snapshot_id = snapshot.snapshot_id
    await engine.dispose()
    return snapshot_id


async def _read_hot_state(session_id: str):
    return await live_sync.get_hot_state(session_id)


async def _events_for(session_id: str) -> list[TeachingSessionEvent]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(
            select(TeachingSessionEvent)
            .where(TeachingSessionEvent.session_id == session_id)
            .order_by(TeachingSessionEvent.sequence),
        )
        rows = list(result.scalars().all())
    await engine.dispose()
    return rows


async def _aggregates_for(session_id: str) -> list[SessionResponseAggregate]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(
            select(SessionResponseAggregate).where(
                SessionResponseAggregate.session_id == session_id,
            ),
        )
        rows = list(result.scalars().all())
    await engine.dispose()
    return rows


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


_POLL_VOTE_BODY = {
    "interaction_id": "i1", "kind": "poll_vote", "payload": {"selected_option_id": "a"},
}


class TestAdvanceSlideLivePathProof:
    """The real "teacher advances the slide" route: proves Postgres append +
    Redis-hot-state + Redis Pub/Sub publish all fire from an actual request."""

    def test_route_persists_the_event_and_updates_redis_hot_state(
        self, client: TestClient,
    ) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-42", "slide_index": 3},
            headers=_bearer(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["current_slide_id"] == "slide-42"
        assert body["last_sequence"] == 1

        rows = anyio.run(_events_for, session.session_id)
        assert len(rows) == 1
        assert rows[0].event_type == "slide_changed"
        assert rows[0].payload == {"slide_id": "slide-42", "slide_index": 3}

        hot_state = anyio.run(_read_hot_state, session.session_id)
        assert hot_state is not None
        assert hot_state.current_slide_id == "slide-42"

    def test_a_token_minted_for_another_session_is_rejected(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        other_session = anyio.run(_create_session)
        token = mint_session_token(other_session, role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-1"},
            headers=_bearer(token),
        )

        assert response.status_code == 403

    def test_a_student_token_cannot_advance_the_slide(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-1"},
            headers=_bearer(token),
        )

        assert response.status_code == 403

    def test_missing_token_is_401(self, client: TestClient) -> None:
        session = anyio.run(_create_session)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/slide", json={"slide_id": "slide-1"},
        )

        assert response.status_code == 401


class TestSubmitResponseIdempotency:
    """Base AC6, end to end: a duplicate Idempotency-Key never double-counts
    TSP-05's aggregate or double-logs the significant event, through the
    real route."""

    def test_duplicate_idempotency_key_only_increments_once(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.STUDENT)
        idempotency_key = f"idem-{uuid4()}"
        body = {
            "interaction_id": "interaction-1",
            "kind": "poll_vote",
            "payload": {"selected_option_id": "a"},
        }

        first = client.post(
            f"/teaching-sessions/{session.session_id}/responses",
            json=body,
            headers={**_bearer(token), "Idempotency-Key": idempotency_key},
        )
        second = client.post(
            f"/teaching-sessions/{session.session_id}/responses",
            json=body,
            headers={**_bearer(token), "Idempotency-Key": idempotency_key},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

        aggregates = anyio.run(_aggregates_for, session.session_id)
        assert len(aggregates) == 1
        assert aggregates[0].attempt_count == 1  # not 2

        events = anyio.run(_events_for, session.session_id)
        assert len(events) == 1
        assert events[0].event_type == "aggregate_updated"
        assert events[0].payload == {
            "interaction_id": "interaction-1",
            "tallies": {"attempt_count": 1, "correct_count": 0},
        }

    def test_missing_idempotency_key_is_rejected(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/responses",
            json=_POLL_VOTE_BODY,
            headers=_bearer(token),
        )

        assert response.status_code == 422

    def test_none_retention_tier_records_no_event(self, client: TestClient) -> None:
        """TSP-01 retention policy governs the event log too (AC): a `none`-tier
        session's student response stays fully ephemeral -- no significant
        event, no broadcast."""
        session = anyio.run(partial(_create_session, retention_tier=RetentionTier.NONE))
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/responses",
            json=_POLL_VOTE_BODY,
            headers={**_bearer(token), "Idempotency-Key": f"idem-{uuid4()}"},
        )

        assert response.status_code == 200
        assert anyio.run(_events_for, session.session_id) == []
        assert anyio.run(_aggregates_for, session.session_id) == []


class TestReconnectFlow:
    """Base AC4: session ID + role token -> current derived state."""

    def test_state_reflects_the_latest_recorded_event(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        controller_token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)
        client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-9"},
            headers=_bearer(controller_token),
        )

        response = client.get(
            f"/teaching-sessions/{session.session_id}/state", headers=_bearer(controller_token),
        )

        assert response.status_code == 200
        assert response.json()["current_slide_id"] == "slide-9"

    def test_state_reports_the_currently_pinned_snapshot_id(self, client: TestClient) -> None:
        """#458 follow-up gap: `/state` reads `TeachingSession.snapshot_id`
        straight from Postgres (not the event-sourced read model), so it's
        always accurate even without any `content_republished` event yet."""
        session = anyio.run(partial(_create_session, snapshot_id="snap-initial"))
        token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = client.get(
            f"/teaching-sessions/{session.session_id}/state", headers=_bearer(token),
        )

        assert response.status_code == 200
        assert response.json()["current_snapshot_id"] == "snap-initial"


class TestContentRoute:
    """#458 follow-up gap: the live sync layer only carried navigation/
    interaction events before this route existed -- this is the fetchable
    reference clients follow for the actual pinned slide content."""

    def test_returns_the_student_safe_rendering_of_the_pinned_snapshot(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        student_html = "<p>Slide content for students</p>"
        snapshot_id = anyio.run(
            partial(_seed_slide_deck_snapshot, run_id, student_html=student_html),
        )
        session = anyio.run(partial(_create_session, snapshot_id=snapshot_id))
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.get(
            f"/teaching-sessions/{session.session_id}/content", headers=_bearer(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["snapshot_id"] == snapshot_id
        assert body["deck_id"] == "deck-1"
        assert body["student_rendered_html"] == student_html
        assert "teacher-only-view" not in response.text
        anyio.run(delete_run, run_id)

    def test_missing_snapshot_is_404(self, client: TestClient) -> None:
        session = anyio.run(partial(_create_session, snapshot_id="snap-does-not-exist"))
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.get(
            f"/teaching-sessions/{session.session_id}/content", headers=_bearer(token),
        )

        assert response.status_code == 404


class TestStreamRoute:
    """Base AC3: SSE broadcast is reachable through the real route and replays
    persisted events via `Last-Event-ID`.

    Drives the registered route function's returned `StreamingResponse`
    directly with a bounded task group + cancel, same hazard-avoidance shape
    `test_teaching_pack_stream_router.py::_read_live_stream_after_commit`
    uses for its own never-terminating live-tail generator -- a real
    blocking HTTP round trip through `TestClient.stream()` against an
    intentionally-infinite SSE generator has no natural end, so this drives
    the same route function object FastAPI dispatches to, without going
    through the HTTP transport.
    """

    def test_stream_replays_persisted_events(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)
        client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-77"},
            headers=_bearer(token),
        )

        first_chunk = anyio.run(_read_first_stream_chunk, session.session_id, token)

        assert "slide_changed" in first_chunk
        assert "id: 1" in first_chunk


async def _read_first_stream_chunk(session_id: str, token: str) -> str:
    from services.gateway.routers.teaching_session_live import stream_session_events
    from services.gateway.teaching_session.tokens import verify_session_token

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        claims = verify_session_token(token)
        response = await stream_session_events(
            session_id, claims=claims, db=db, last_event_id="0",
        )
        first_chunk = ""
        async with anyio.create_task_group() as task_group:
            async def _read_one() -> None:
                nonlocal first_chunk
                async for chunk in response.body_iterator:
                    first_chunk = chunk.decode() if isinstance(chunk, bytes) else chunk
                    break
                task_group.cancel_scope.cancel()

            task_group.start_soon(_read_one)
    await engine.dispose()
    return first_chunk
