from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.agents.pipeline_v2.stages import PipelineV2Stage
from services.gateway.models import Base, Run, RunStatus
from services.gateway.pipeline_v2_models import (
    PipelineV2EventVisibility,
    RunEvent,
    RunStatusHistory,
)
from services.gateway.pipeline_v2_store import (
    ArtifactSnapshotCreate,
    PipelineV2EventCreate,
    PipelineV2RunCreate,
    PipelineV2RunStore,
    PipelineV2StatusTransition,
)
from services.gateway.pipeline_v2_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_events" not in existing_tables:
            pytest.skip("Pipeline V2 tables are not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestPipelineV2Store:
    async def test_create_run_reads_back_for_matching_teacher(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        teacher_id = TeacherId("teacher-a")
        store = PipelineV2RunStore(session)

        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach fractions",
            class_info={"grade": 5, "subject": "math"},
        ))
        await session.commit()

        run = await store.get_run(run_id, teacher_id)

        assert run is not None
        assert run.run_id == run_id
        assert run.teacher_id == teacher_id
        assert run.status is RunStatus.PENDING
        assert run.raw_request == "Teach fractions"

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


    async def test_get_run_returns_none_for_other_teacher(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        store = PipelineV2RunStore(session)

        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach cells",
            class_info={"grade": 6},
        ))
        await session.commit()

        run = await store.get_run(run_id, TeacherId("teacher-b"))

        assert run is None

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_transition_status_persists_history(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        teacher_id = TeacherId("teacher-a")
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach magnets",
            class_info={"grade": 3},
        ))

        await store.transition_status(PipelineV2StatusTransition(
            run_id=run_id,
            status=RunStatus.PLANNING,
            stage=PipelineV2Stage.PLANNING_BLUEPRINT.value,
            reason="blueprint started",
        ))
        await session.commit()

        run = await store.get_run(run_id, teacher_id)
        history_result = await session.execute(
            select(RunStatusHistory)
            .where(RunStatusHistory.run_id == run_id)
            .order_by(RunStatusHistory.id),
        )
        history = list(history_result.scalars().all())

        assert run is not None
        assert run.status is RunStatus.PLANNING
        assert [entry.status for entry in history] == [RunStatus.PENDING, RunStatus.PLANNING]
        assert history[-1].reason == "blueprint started"

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_events_replay_in_sequence_order(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach plants",
            class_info={"grade": 4},
        ))

        first = await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name=PipelineV2Stage.SETUP_CONTRACT.started_event,
            visibility=PipelineV2EventVisibility.TEACHER,
            stage=PipelineV2Stage.SETUP_CONTRACT,
        ))
        second = await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name=PipelineV2Stage.SETUP_CONTRACT.completed_event,
            visibility=PipelineV2EventVisibility.ADMIN,
            stage=PipelineV2Stage.SETUP_CONTRACT,
        ))
        await session.commit()

        replayed = await store.replay_events(run_id, after_sequence=0)

        assert first.sequence == 1
        assert second.sequence == 2
        assert [event.sequence for event in replayed] == [1, 2]
        assert [event.event_name for event in replayed] == [
            PipelineV2Stage.SETUP_CONTRACT.started_event,
            PipelineV2Stage.SETUP_CONTRACT.completed_event,
        ]

        after_first = await store.replay_events(run_id, after_sequence=1)

        assert [event.sequence for event in after_first] == [2]

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_concurrent_event_writes_remain_monotonic(self) -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        run_id = RunId(f"test-{uuid4()}")
        async with session_factory() as setup_session:
            store = PipelineV2RunStore(setup_session)
            await store.create_run(PipelineV2RunCreate(
                run_id=run_id,
                teacher_id=TeacherId("teacher-a"),
                raw_request="Teach forces",
                class_info={"grade": 4},
            ))
            await setup_session.commit()

        async def write_one(event_name: str) -> None:
            async with session_factory() as write_session:
                store = PipelineV2RunStore(write_session)
                await store.write_event(PipelineV2EventCreate(
                    run_id=run_id,
                    event_name=event_name,
                    visibility=PipelineV2EventVisibility.INTERNAL,
                    stage=PipelineV2Stage.SETUP_CONTRACT,
                ))
                await write_session.commit()

        async with anyio.create_task_group() as task_group:
            for index in range(5):
                task_group.start_soon(write_one, f"event-{index}")

        async with session_factory() as check_session:
            result = await check_session.execute(
                select(RunEvent.sequence)
                .where(RunEvent.run_id == run_id)
                .order_by(RunEvent.sequence),
            )
            sequences = list(result.scalars().all())
            await check_session.execute(delete(Run).where(Run.run_id == run_id))
            await check_session.commit()
        await engine.dispose()

        assert sequences == [1, 2, 3, 4, 5]

    async def test_snapshot_hash_is_deterministic_and_queryable(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach water cycle",
            class_info={"grade": 5},
        ))

        content_hash = await store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="lesson",
            content_json={"title": "Water Cycle"},
            rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
            renderer_version="test-renderer@1",
        ))
        await session.commit()

        exists = await store.has_snapshot(content_hash)

        assert len(content_hash) == 64
        assert exists is True

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_snapshot_duplicate_content_reuses_hash(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach clouds",
            class_info={"grade": 2},
        ))
        snapshot = ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="lesson",
            content_json={"title": "Clouds"},
            rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
            renderer_version="test-renderer@1",
        )

        first_hash = await store.create_snapshot(snapshot)
        second_hash = await store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="lesson",
            content_json={"title": "Clouds"},
            rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
            renderer_version="test-renderer@1",
        ))
        await session.commit()

        assert second_hash == first_hash

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


def test_pipeline_v2_tables_are_registered_in_metadata() -> None:
    assert "public.run_status_history" in Base.metadata.tables
    assert "public.run_events" in Base.metadata.tables
    assert "public.artifact_snapshots" in Base.metadata.tables
