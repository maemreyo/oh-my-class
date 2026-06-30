"""Reconcile/sweep tests for UnitOrchestrator (td-010).

Tests the ``reconcile_units()`` sweep function which is called by the
background sweeper to advance all live UNIT_PARENT runs.

All tests require a live PostgreSQL instance and are marked accordingly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.lesson_sequence import LessonSequence, SessionPlan
from services.gateway.models import Base, Run, RunStatus, UnitRole
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.unit_orchestrator import reconcile_units
from services.gateway.unit_run_store import UnitParentRunCreate, UnitRunStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = pytest.mark.asyncio

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

_METHODOLOGY = "why_wrong_reasoning"


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


def _single_session_sequence(session_id: str = "S01") -> dict:
    seq = LessonSequence(
        topic="Sweep unit",
        grade_level="Grade 9",
        subject="Chemistry",
        locale="en",
        total_sessions=1,
        total_duration_minutes=30,
        sessions=[
            SessionPlan(
                session_id=session_id,
                order_index=1,
                title=f"Session {session_id}",
                sub_topic="Sweep test",
                duration_minutes=30,
                learning_objectives=["Learn sweep"],
                bloom_level_primary="apply",
                methodology_primary=_METHODOLOGY,
                prerequisite_sessions=[],
            )
        ],
        grounding_status="grounded",
        confidence=0.88,
        rationale="Sweep test fixture",
    )
    return seq.model_dump()


async def _delete_unit(session: AsyncSession, parent_id: RunId) -> None:
    await session.execute(
        delete(Run).where((Run.run_id == parent_id) | (Run.parent_run_id == parent_id))
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="requires real DB")
class TestSweepAdvancesUnit:
    async def test_sweep_advances_unit(self, session: AsyncSession) -> None:
        """reconcile_units() spawns a child session for a ready UNIT_PARENT run.

        Setup:
        - Create a UNIT_PARENT run with a single-session LessonSequence.
        - Status remains PENDING (not yet spawned).
        - Call reconcile_units() to simulate the sweeper tick.

        Expected: a UNIT_SESSION child row is created for session S01.
        """
        parent_id = RunId(f"unit-sweep-{uuid4()}")
        unit_run_store = UnitRunStore(session)

        await unit_run_store.create_parent_run(UnitParentRunCreate(
            run_id=parent_id,
            teacher_id=TeacherId("teacher-sweep"),
            raw_request="Generate sweep unit",
            class_info={"grade": 9, "subject": "Chemistry"},
            lesson_sequence=_single_session_sequence("S01"),
        ))
        await session.commit()

        # Run the sweep.
        await reconcile_units(session)
        await session.commit()

        # Verify the child was spawned.
        result = await session.execute(
            select(Run).where(
                Run.parent_run_id == parent_id,
                Run.unit_role == UnitRole.UNIT_SESSION,
            )
        )
        children = result.scalars().all()

        assert len(children) >= 1, (
            "Expected reconcile_units() to spawn at least one child session"
        )
        assert children[0].session_id == "S01"
        assert children[0].status == RunStatus.PENDING

        await _delete_unit(session, parent_id)

    async def test_sweep_skips_terminal_parent_runs(self, session: AsyncSession) -> None:
        """reconcile_units() must not process COMPLETED or FAILED parent runs.

        A COMPLETED parent has no sessions left to spawn.  The sweep function
        should ignore it entirely.
        """
        parent_id = RunId(f"unit-sweep-done-{uuid4()}")
        unit_run_store = UnitRunStore(session)

        await unit_run_store.create_parent_run(UnitParentRunCreate(
            run_id=parent_id,
            teacher_id=TeacherId("teacher-sweep-done"),
            raw_request="Generate completed unit",
            class_info={"grade": 9, "subject": "Chemistry"},
            lesson_sequence=_single_session_sequence("S01"),
        ))
        # Mark the parent as COMPLETED before the sweep.
        from sqlalchemy import update
        await session.execute(
            update(Run).where(Run.run_id == parent_id).values(status=RunStatus.COMPLETED)
        )
        await session.commit()

        await reconcile_units(session)
        await session.commit()

        # No child should have been spawned.
        result = await session.execute(
            select(Run).where(
                Run.parent_run_id == parent_id,
                Run.unit_role == UnitRole.UNIT_SESSION,
            )
        )
        children = result.scalars().all()
        assert not children, (
            "reconcile_units() must not spawn sessions for a COMPLETED parent run"
        )

        await _delete_unit(session, parent_id)

    async def test_sweep_idempotent_second_call(self, session: AsyncSession) -> None:
        """Calling reconcile_units() twice must not create duplicate child rows."""
        parent_id = RunId(f"unit-sweep-idempotent-{uuid4()}")
        unit_run_store = UnitRunStore(session)

        await unit_run_store.create_parent_run(UnitParentRunCreate(
            run_id=parent_id,
            teacher_id=TeacherId("teacher-sweep-idem"),
            raw_request="Generate idempotent sweep unit",
            class_info={"grade": 9, "subject": "Chemistry"},
            lesson_sequence=_single_session_sequence("S01"),
        ))
        await session.commit()

        # First sweep — spawns S01.
        await reconcile_units(session)
        await session.commit()

        # Second sweep — S01 is now in children_states; must not spawn again.
        await reconcile_units(session)
        await session.commit()

        result = await session.execute(
            select(Run).where(
                Run.parent_run_id == parent_id,
                Run.unit_role == UnitRole.UNIT_SESSION,
                Run.session_id == "S01",
            )
        )
        children = result.scalars().all()
        assert len(children) == 1, (
            f"Expected exactly 1 child row after two sweep calls, found {len(children)}"
        )

        await _delete_unit(session, parent_id)
