from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus, UnitRole
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.unit_run_store import (
    UnitLifecycle,
    UnitParentRunCreate,
    UnitRunStore,
    UnitSessionRunCreate,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.runs" not in existing_tables:
            pytest.skip("Runs table is not present")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestUnitPersistence:
    async def test_lists_children_by_parent_in_session_order(self, session: AsyncSession) -> None:
        parent_id = RunId(f"unit-parent-{uuid4()}")
        store = UnitRunStore(session)

        await _create_unit_parent(store, parent_id)
        await _create_child(store, parent_id, "S03", 3)
        await _create_child(store, parent_id, "S01", 1)
        await _create_child(store, parent_id, "S02", 2)
        await session.commit()

        children = await store.list_children(parent_id)

        assert [child.session_id for child in children] == ["S01", "S02", "S03"]
        assert [child.session_index for child in children] == [1, 2, 3]
        assert all(child.parent_run_id == parent_id for child in children)

        await _delete_unit(session, parent_id)

    async def test_computes_unit_status_from_child_rows(self, session: AsyncSession) -> None:
        parent_id = RunId(f"unit-status-{uuid4()}")
        store = UnitRunStore(session)

        await _create_unit_parent(store, parent_id)
        first = await _create_child(store, parent_id, "S01", 1)
        second = await _create_child(store, parent_id, "S02", 2)
        third = await _create_child(store, parent_id, "S03", 3)
        await session.execute(
            update(Run)
            .where(Run.run_id == first)
            .values(status=RunStatus.COMPLETED),
        )
        await session.execute(
            update(Run)
            .where(Run.run_id == second)
            .values(status=RunStatus.GENERATING),
        )
        await session.execute(
            update(Run)
            .where(Run.run_id == third)
            .values(status=RunStatus.FAILED),
        )
        await session.commit()

        status = await store.compute_unit_status(parent_id)

        assert status.lifecycle is UnitLifecycle.PARTIALLY_COMPLETE
        assert status.total_sessions == 3
        assert status.completed_sessions == 1
        assert status.active_sessions == 1
        assert status.failed_sessions == 1

        await _delete_unit(session, parent_id)

    async def test_complete_unit_status_requires_all_children_completed(self, session: AsyncSession) -> None:
        parent_id = RunId(f"unit-complete-{uuid4()}")
        store = UnitRunStore(session)

        await _create_unit_parent(store, parent_id)
        first = await _create_child(store, parent_id, "S01", 1)
        second = await _create_child(store, parent_id, "S02", 2)
        await session.execute(
            update(Run)
            .where(Run.run_id.in_([first, second]))
            .values(status=RunStatus.COMPLETED),
        )
        await session.commit()

        status = await store.compute_unit_status(parent_id)

        assert status.lifecycle is UnitLifecycle.COMPLETE
        assert status.completed_sessions == 2

        await _delete_unit(session, parent_id)

    async def test_parent_lesson_sequence_round_trips(self, session: AsyncSession) -> None:
        parent_id = RunId(f"unit-sequence-{uuid4()}")
        store = UnitRunStore(session)
        lesson_sequence = {"unit_title": "Fractions", "sessions": [{"id": "S01"}]}

        await store.create_parent_run(UnitParentRunCreate(
            run_id=parent_id,
            teacher_id=TeacherId("teacher-unit"),
            raw_request="Plan a unit about fractions",
            class_info={"grade": 5, "subject": "math"},
            lesson_sequence=lesson_sequence,
        ))
        await session.commit()

        restored = await store.get_lesson_sequence(parent_id)

        assert restored == lesson_sequence

        await _delete_unit(session, parent_id)

    async def test_standalone_run_round_trips_with_unit_defaults(self, session: AsyncSession) -> None:
        run_id = RunId(f"standalone-{uuid4()}")
        teacher_id = TeacherId("teacher-standalone")
        store = TeachingPackRunStore(session)

        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach a standalone lesson",
            class_info={"grade": 4, "subject": "science"},
        ))
        await session.commit()

        result = await session.execute(select(Run).where(Run.run_id == run_id))
        run = result.scalar_one()

        assert run.unit_role is UnitRole.STANDALONE
        assert run.parent_run_id is None
        assert run.session_id is None
        assert run.session_index is None
        assert run.lesson_sequence is None
        assert run.shared_research is None
        assert run.persona_snapshot is None

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


class TestUnitPersistenceMigration:
    async def test_unit_columns_constraints_and_indexes_exist(self, engine: AsyncEngine) -> None:
        async with engine.connect() as connection:
            columns = await connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'runs' "
                "AND column_name IN "
                "('parent_run_id', 'session_id', 'session_index', 'unit_role', "
                "'lesson_sequence', 'shared_research', 'persona_snapshot')",
            ))
            index_row = await connection.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'runs' "
                "AND indexname = 'ix_runs_parent_run_id'",
            ))
            constraint_row = await connection.execute(text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "AND table_name = 'runs' "
                "AND constraint_name = 'uq_runs_parent_session'",
            ))

        assert set(columns.scalars().all()) == {
            "parent_run_id",
            "session_id",
            "session_index",
            "unit_role",
            "lesson_sequence",
            "shared_research",
            "persona_snapshot",
        }
        assert index_row.scalar_one_or_none() == "ix_runs_parent_run_id"
        assert constraint_row.scalar_one_or_none() == "uq_runs_parent_session"


async def _create_unit_parent(store: UnitRunStore, parent_id: RunId) -> None:
    await store.create_parent_run(UnitParentRunCreate(
        run_id=parent_id,
        teacher_id=TeacherId("teacher-unit"),
        raw_request="Plan a unit about fractions",
        class_info={"grade": 5, "subject": "math"},
        lesson_sequence={"unit_title": "Fractions", "sessions": []},
    ))


async def _create_child(
    store: UnitRunStore,
    parent_id: RunId,
    session_id: str,
    session_index: int,
) -> RunId:
    run_id = RunId(f"unit-child-{session_id}-{uuid4()}")
    await store.create_child_run(UnitSessionRunCreate(
        run_id=run_id,
        parent_run_id=parent_id,
        teacher_id=TeacherId("teacher-unit"),
        session_id=session_id,
        session_index=session_index,
        raw_request=f"Generate session {session_id}",
        class_info={"grade": 5, "subject": "math"},
    ))
    return run_id


async def _delete_unit(session: AsyncSession, parent_id: RunId) -> None:
    await session.execute(delete(Run).where((Run.run_id == parent_id) | (Run.parent_run_id == parent_id)))
    await session.commit()
