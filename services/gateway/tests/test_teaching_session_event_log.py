from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base
from services.gateway.teaching_session import service
from services.gateway.teaching_session.event_log import (
    append_event,
    record_event,
    recover_read_model,
    replay_events,
)
from services.gateway.teaching_session.events import SessionEventType
from services.gateway.teaching_session.models import RetentionTier, TeachingSessionEvent
from services.gateway.teaching_session.tokens import SessionRole

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.teaching_session_events" not in existing_tables:
            pytest.skip("teaching_session_events table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


async def _make_session(db: AsyncSession) -> str:
    session_id = f"session-{uuid4()}"
    await service.create_session(
        db,
        session_id=session_id,
        teacher_id=f"teacher-{uuid4()}",
        deck_id="deck-1",
        snapshot_id="snap-1",
        retention_tier=RetentionTier.AGGREGATE,
    )
    await db.flush()
    return session_id


class TestAppendEvent:
    async def test_assigns_increasing_per_session_sequence(self, db: AsyncSession) -> None:
        session_id = await _make_session(db)
        row1, created1 = await append_event(
            db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1"},
        )
        row2, created2 = await append_event(
            db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s2"},
        )
        assert created1 is True
        assert created2 is True
        assert row1.sequence == 1
        assert row2.sequence == 2

    async def test_sequence_is_scoped_per_session(self, db: AsyncSession) -> None:
        session_a = await _make_session(db)
        session_b = await _make_session(db)
        row_a, _ = await append_event(
            db, session_id=session_a, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1"},
        )
        row_b, _ = await append_event(
            db, session_id=session_b, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1"},
        )
        assert row_a.sequence == 1
        assert row_b.sequence == 1

    async def test_duplicate_idempotency_key_returns_the_original_row_uncreated(
        self, db: AsyncSession,
    ) -> None:
        session_id = await _make_session(db)
        key = f"idem-{uuid4()}"
        first, created_first = await append_event(
            db, session_id=session_id, event_type=SessionEventType.AGGREGATE_UPDATED,
            actor_role=SessionRole.STUDENT,
            payload={"interaction_id": "i1", "tallies": {"attempt_count": 1, "correct_count": 1}},
            idempotency_key=key,
        )
        second, created_second = await append_event(
            db, session_id=session_id, event_type=SessionEventType.AGGREGATE_UPDATED,
            actor_role=SessionRole.STUDENT,
            payload={"interaction_id": "i1", "tallies": {"attempt_count": 99, "correct_count": 99}},
            idempotency_key=key,
        )
        assert created_first is True
        assert created_second is False
        assert second.event_id == first.event_id
        assert second.payload == first.payload  # the retried payload never overwrote it

        result = await db.execute(
            select(TeachingSessionEvent).where(TeachingSessionEvent.session_id == session_id),
        )
        assert len(result.scalars().all()) == 1  # no duplicate row was inserted


class TestReplayEvents:
    async def test_replay_after_sequence_returns_only_later_events(self, db: AsyncSession) -> None:
        session_id = await _make_session(db)
        for slide_id in ("s1", "s2", "s3"):
            await append_event(
                db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
                actor_role=SessionRole.CONTROLLER, payload={"slide_id": slide_id},
            )
        rows = await replay_events(db, session_id, after_sequence=1)
        assert [row.sequence for row in rows] == [2, 3]


class TestRecoverReadModel:
    async def test_recovers_current_slide_from_replayed_events(self, db: AsyncSession) -> None:
        session_id = await _make_session(db)
        for slide_id in ("s1", "s2", "s3"):
            await append_event(
                db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
                actor_role=SessionRole.CONTROLLER, payload={"slide_id": slide_id},
            )
        state = await recover_read_model(db, session_id)
        assert state.current_slide_id == "s3"
        assert state.last_sequence == 3

    async def test_recovery_limit_still_reflects_last_write_within_the_window(
        self, db: AsyncSession,
    ) -> None:
        """AC (amendment): reconstruct state by replaying the last N events."""
        session_id = await _make_session(db)
        for slide_id in ("s1", "s2", "s3", "s4"):
            await append_event(
                db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
                actor_role=SessionRole.CONTROLLER, payload={"slide_id": slide_id},
            )
        state = await recover_read_model(db, session_id, limit=2)
        assert state.current_slide_id == "s4"  # last-write-wins even with a narrow window


class TestRecordEvent:
    async def test_record_event_computes_the_next_derived_state(self, db: AsyncSession) -> None:
        session_id = await _make_session(db)
        recorded = await record_event(
            db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1"},
        )
        assert recorded.duplicate is False
        assert recorded.read_model.current_slide_id == "s1"
        assert recorded.read_model.last_sequence == 1

    async def test_record_event_folds_onto_prior_state_without_redis(
        self, db: AsyncSession,
    ) -> None:
        """No Redis client is passed anywhere in this test module -- `record_event`
        falls back to Postgres recovery for "previous state" when Redis is
        unreachable (the module-level singleton client here points at a real,
        reachable dev Redis, so this exercises the *recovery* path, not a
        Redis outage -- see test_teaching_session_live_sync.py for the outage
        case)."""
        session_id = await _make_session(db)
        await record_event(
            db, session_id=session_id, event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1"},
        )
        second = await record_event(
            db, session_id=session_id, event_type=SessionEventType.BRANCH_SELECTED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "s1", "branch_id": "b1"},
        )
        assert second.read_model.current_branch_id == "b1"
        assert second.read_model.last_sequence == 2
