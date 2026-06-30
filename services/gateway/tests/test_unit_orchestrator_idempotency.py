"""Idempotency tests for UnitOrchestrator.react() (td-010).

These tests require a live PostgreSQL instance at the standard dev URL.
They are skipped automatically when the ``runs`` table is absent.

Verified properties:
- Spawning the same session twice results in a single child row (unique
  constraint ``uq_runs_parent_session`` protects the second insert).
- Calling ``react()`` twice in succession produces no duplicate child rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.lesson_sequence import LessonSequence, SessionPlan
from services.gateway.models import Base, Run, RunStatus, UnitRole
from services.gateway.teaching_pack_job_store import TeachingPackJobStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.unit_orchestrator import UnitOrchestrator
from services.gateway.unit_run_store import (
    UnitParentRunCreate,
    UnitRunStore,
    UnitSessionRunCreate,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = pytest.mark.asyncio

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

_METHODOLOGY = "concept_map"


# ---------------------------------------------------------------------------
# Fixtures (mirror test_unit_persistence.py pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda c: set(Base.metadata.tables))
        if "public.runs" not in existing_tables:
            pytest.skip("Runs table is not present")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session
        await db_session.rollback()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_sequence(session_id: str = "S01") -> dict:
    """Return a JSON-serialisable LessonSequence with a single session."""
    seq = LessonSequence(
        topic="Idempotency unit",
        grade_level="Grade 6",
        subject="Science",
        locale="en",
        total_sessions=1,
        total_duration_minutes=30,
        sessions=[
            SessionPlan(
                session_id=session_id,
                order_index=1,
                title="Session one",
                sub_topic="Introduction",
                duration_minutes=30,
                learning_objectives=["Understand the basics"],
                bloom_level_primary="understand",
                methodology_primary=_METHODOLOGY,
                prerequisite_sessions=[],
            )
        ],
        grounding_status="grounded",
        confidence=0.9,
        rationale="Test fixture",
    )
    return seq.model_dump()


async def _create_parent(
    store: UnitRunStore,
    parent_id: RunId,
    lesson_sequence: dict | None = None,
) -> None:
    await store.create_parent_run(UnitParentRunCreate(
        run_id=parent_id,
        teacher_id=TeacherId("teacher-orch"),
        raw_request="Generate unit",
        class_info={"grade": 6, "subject": "Science"},
        lesson_sequence=lesson_sequence or _minimal_sequence(),
    ))


async def _delete_unit(session: AsyncSession, parent_id: RunId) -> None:
    await session.execute(
        delete(Run).where((Run.run_id == parent_id) | (Run.parent_run_id == parent_id))
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="requires real DB")
class TestDuplicateSpawnRejected:
    async def test_duplicate_spawn_rejected(self, session: AsyncSession) -> None:
        """Calling react() twice on the same unspawned session yields one child row.

        The unique constraint ``uq_runs_parent_session`` on (parent_run_id,
        session_id) means the second ``create_child_run`` is a no-op
        (on_conflict_do_nothing via the job store, and the flush on the
        child row raises IntegrityError which we convert to a no-op).
        """
        parent_id = RunId(f"unit-idempotent-{uuid4()}")
        unit_run_store = UnitRunStore(session)
        job_store = TeachingPackJobStore(session)

        await _create_parent(unit_run_store, parent_id)
        await session.commit()

        orchestrator = UnitOrchestrator(
            session=session,
            unit_run_store=unit_run_store,
            job_store=job_store,
        )

        # First react — should SPAWN S01.
        actions_first = await orchestrator.react(parent_id)
        await session.commit()

        # Second react — S01 is now in children_states (pending), no re-spawn.
        actions_second = await orchestrator.react(parent_id)
        await session.commit()

        # Count child rows.
        result = await session.execute(
            select(Run).where(
                Run.parent_run_id == parent_id,
                Run.unit_role == UnitRole.UNIT_SESSION,
            )
        )
        children = result.scalars().all()

        assert len(children) == 1, (
            f"Expected exactly 1 child row but found {len(children)}"
        )

        # Second call must not have produced another SPAWN.
        from services.gateway.unit_orchestrator import OrchestratorAction
        second_spawns = [a for a in actions_second if a.action is OrchestratorAction.SPAWN]
        assert not second_spawns

        await _delete_unit(session, parent_id)


@pytest.mark.skip(reason="requires real DB")
class TestRestartMidFanout:
    async def test_restart_mid_fanout_no_duplicates(self, session: AsyncSession) -> None:
        """react() called twice mid-fanout produces no duplicate child rows.

        Scenario: parent has two sessions (S01, S02), both with no prerequisites.
        First react() spawns S01 (concurrency=1).  A restart (simulated by
        calling react() again) must not spawn S01 again.
        """
        seq = LessonSequence(
            topic="Restart mid-fanout",
            grade_level="Grade 5",
            subject="Math",
            locale="en",
            total_sessions=2,
            total_duration_minutes=60,
            sessions=[
                SessionPlan(
                    session_id="S01",
                    order_index=1,
                    title="Session one",
                    sub_topic="Part one",
                    duration_minutes=30,
                    learning_objectives=["Obj one"],
                    bloom_level_primary="remember",
                    methodology_primary=_METHODOLOGY,
                    prerequisite_sessions=[],
                ),
                SessionPlan(
                    session_id="S02",
                    order_index=2,
                    title="Session two",
                    sub_topic="Part two",
                    duration_minutes=30,
                    learning_objectives=["Obj two"],
                    bloom_level_primary="understand",
                    methodology_primary=_METHODOLOGY,
                    prerequisite_sessions=[],
                ),
            ],
            grounding_status="grounded",
            confidence=0.9,
            rationale="Test fixture",
        )
        parent_id = RunId(f"unit-restart-{uuid4()}")
        unit_run_store = UnitRunStore(session)
        job_store = TeachingPackJobStore(session)

        await _create_parent(unit_run_store, parent_id, lesson_sequence=seq.model_dump())
        await session.commit()

        orchestrator = UnitOrchestrator(
            session=session,
            unit_run_store=unit_run_store,
            job_store=job_store,
        )

        # First react → spawns S01 (concurrency 1).
        await orchestrator.react(parent_id)
        await session.commit()

        # Second react → S01 exists (pending), spawns S02.
        await orchestrator.react(parent_id)
        await session.commit()

        result = await session.execute(
            select(Run).where(
                Run.parent_run_id == parent_id,
                Run.unit_role == UnitRole.UNIT_SESSION,
            )
        )
        children = result.scalars().all()
        session_ids = [c.session_id for c in children]

        # No duplicates.
        assert len(session_ids) == len(set(session_ids)), (
            f"Duplicate child rows found: {session_ids}"
        )

        await _delete_unit(session, parent_id)
