"""Failure-path tests for UnitOrchestrator.react() (td-010).

Tests verify:
- A failed child session does not prevent its sibling sessions (with
  satisfied prerequisites) from being spawned.
- Retrying a failed session reuses the existing child row rather than
  creating a new one.
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
from services.gateway.unit_orchestrator import OrchestratorAction, UnitOrchestrator
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

_METHODOLOGY = "active_recall"


# ---------------------------------------------------------------------------
# Fixtures
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


async def _delete_unit(session: AsyncSession, parent_id: RunId) -> None:
    await session.execute(
        delete(Run).where((Run.run_id == parent_id) | (Run.parent_run_id == parent_id))
    )
    await session.commit()


def _two_sibling_sequence() -> LessonSequence:
    """Two independent sessions A and B — no prerequisites between them."""
    return LessonSequence(
        topic="Failure unit",
        grade_level="Grade 7",
        subject="History",
        locale="en",
        total_sessions=2,
        total_duration_minutes=60,
        sessions=[
            SessionPlan(
                session_id="A",
                order_index=1,
                title="Session A",
                sub_topic="Part A",
                duration_minutes=30,
                learning_objectives=["Learn A"],
                bloom_level_primary="remember",
                methodology_primary=_METHODOLOGY,
                prerequisite_sessions=[],
            ),
            SessionPlan(
                session_id="B",
                order_index=2,
                title="Session B",
                sub_topic="Part B",
                duration_minutes=30,
                learning_objectives=["Learn B"],
                bloom_level_primary="understand",
                methodology_primary=_METHODOLOGY,
                prerequisite_sessions=[],
            ),
        ],
        grounding_status="grounded",
        confidence=0.85,
        rationale="Test fixture",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="requires real DB")
class TestFailedSessionKeepsUnitAlive:
    async def test_failed_session_keeps_unit_alive(self, session: AsyncSession) -> None:
        """When session A fails, session B (no dependency on A) is still spawned.

        Simulates: A was spawned and transitioned to FAILED.  A fresh react()
        call should spawn B (not block it) and must NOT emit MARK_COMPLETE.
        """
        sequence = _two_sibling_sequence()
        parent_id = RunId(f"unit-failure-alive-{uuid4()}")
        unit_run_store = UnitRunStore(session)
        job_store = TeachingPackJobStore(session)

        await unit_run_store.create_parent_run(UnitParentRunCreate(
            run_id=parent_id,
            teacher_id=TeacherId("teacher-failure"),
            raw_request="Generate failure unit",
            class_info={"grade": 7, "subject": "History"},
            lesson_sequence=sequence.model_dump(),
        ))

        # Manually create a FAILED child row for session A.
        child_a_id = RunId(f"unit-child-A-{uuid4()}")
        await unit_run_store.create_child_run(UnitSessionRunCreate(
            run_id=child_a_id,
            parent_run_id=parent_id,
            teacher_id=TeacherId("teacher-failure"),
            session_id="A",
            session_index=1,
            raw_request="Generate session A",
            class_info={"grade": 7, "subject": "History"},
        ))
        await session.execute(
            update(Run).where(Run.run_id == child_a_id).values(status=RunStatus.FAILED)
        )
        await session.commit()

        orchestrator = UnitOrchestrator(
            session=session,
            unit_run_store=unit_run_store,
            job_store=job_store,
        )
        actions = await orchestrator.react(parent_id)
        await session.commit()

        spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
        assert any(a.session_id == "B" for a in spawns), (
            "Expected session B to be spawned when A failed but B has no dependency on A"
        )

        complete_actions = [a for a in actions if a.action is OrchestratorAction.MARK_COMPLETE]
        assert not complete_actions

        await _delete_unit(session, parent_id)


@pytest.mark.skip(reason="requires real DB")
class TestRetryResumesExistingChild:
    async def test_retry_resumes_existing_child(self, session: AsyncSession) -> None:
        """Retrying a failed session must not create a second child row.

        Scenario: session A was spawned and failed.  The orchestrator must
        not create a second ``UNIT_SESSION`` row for A — the existing failed
        row should be the one the worker eventually picks up for retry.

        This test verifies the uniqueness guarantee: the second react() call
        finds A in ``children_states`` (status=FAILED) and does not attempt
        to spawn it again, so the total child count for session A remains 1.
        """
        sequence = LessonSequence(
            topic="Retry unit",
            grade_level="Grade 8",
            subject="Physics",
            locale="en",
            total_sessions=1,
            total_duration_minutes=30,
            sessions=[
                SessionPlan(
                    session_id="A",
                    order_index=1,
                    title="Session A",
                    sub_topic="Retry me",
                    duration_minutes=30,
                    learning_objectives=["Learn retry"],
                    bloom_level_primary="apply",
                    methodology_primary=_METHODOLOGY,
                    prerequisite_sessions=[],
                )
            ],
            grounding_status="grounded",
            confidence=0.8,
            rationale="Test fixture",
        )
        parent_id = RunId(f"unit-retry-{uuid4()}")
        unit_run_store = UnitRunStore(session)
        job_store = TeachingPackJobStore(session)

        await unit_run_store.create_parent_run(UnitParentRunCreate(
            run_id=parent_id,
            teacher_id=TeacherId("teacher-retry"),
            raw_request="Generate retry unit",
            class_info={"grade": 8, "subject": "Physics"},
            lesson_sequence=sequence.model_dump(),
        ))

        # Spawn and immediately fail session A.
        child_a_id = RunId(f"unit-child-A-retry-{uuid4()}")
        await unit_run_store.create_child_run(UnitSessionRunCreate(
            run_id=child_a_id,
            parent_run_id=parent_id,
            teacher_id=TeacherId("teacher-retry"),
            session_id="A",
            session_index=1,
            raw_request="Generate session A",
            class_info={"grade": 8, "subject": "Physics"},
        ))
        await session.execute(
            update(Run).where(Run.run_id == child_a_id).values(status=RunStatus.FAILED)
        )
        await session.commit()

        orchestrator = UnitOrchestrator(
            session=session,
            unit_run_store=unit_run_store,
            job_store=job_store,
        )

        # react() should NOT spawn A again (it is already in children_states).
        actions = await orchestrator.react(parent_id)
        await session.commit()

        spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
        assert not any(a.session_id == "A" for a in spawns), (
            "react() must not spawn session A when it is already present as FAILED"
        )

        # Verify exactly one child row exists for session A.
        result = await session.execute(
            select(Run).where(
                Run.parent_run_id == parent_id,
                Run.session_id == "A",
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1, (
            f"Expected exactly 1 child row for session A, found {len(rows)}"
        )

        await _delete_unit(session, parent_id)
