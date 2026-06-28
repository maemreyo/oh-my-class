from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.artifact_workflow import ArtifactWorkflowState, ArtifactWorkflowStatus
from packages.agents.teaching_pack.stages import TeachingPackStage
from services.gateway.models import Base, Run
from services.gateway.teaching_pack_control_store import TeachingPackControlStore
from services.gateway.teaching_pack_models import ArtifactWorkflow, TeachingPackEventVisibility
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackRunCreate,
    TeachingPackRunStore,
)
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.artifact_workflows" not in tables:
            pytest.skip("Teaching Pack artifact workflow table is not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestArtifactWorkflowPersistence:
    async def test_workflow_state_round_trips_full_issue_007_fields(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)
        state = ArtifactWorkflowState(
            workflow_id=f"workflow-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-lesson",
            artifact_type="lesson",
            status="passed",
            attempts=2,
            contract_revision_id=3,
            research_guidance_id="guidance-lesson",
            validation_status="passed",
            judge_status="passed",
            snapshot_refs=["snapshot-1"],
            last_error=None,
        )

        store = TeachingPackControlStore(session)
        await store.upsert_artifact_workflow_state(state)
        await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.artifact.completed",
            visibility=TeachingPackEventVisibility.TEACHER,
            stage=TeachingPackStage.ARTIFACT_WORKFLOW,
            payload={"artifact_id": "artifact-lesson", "artifact_type": "lesson"},
        ))
        await session.commit()

        persisted = await store.get_artifact_workflow_state(run_id, "artifact-lesson")
        events = await TeachingPackRunStore(session).replay_events(run_id)

        assert persisted == state
        assert events[-1].event_name == "teaching_pack.artifact.completed"
        await _delete_run(session, run_id)

    async def test_workflow_state_update_does_not_duplicate_record(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)
        store = TeachingPackControlStore(session)
        queued = _state(run_id, status="queued", attempts=0, last_error=None)
        failed = _state(run_id, status="failed", attempts=1, last_error="timeout: provider")

        await store.upsert_artifact_workflow_state(queued)
        await store.upsert_artifact_workflow_state(failed)
        await session.commit()

        persisted = await store.get_artifact_workflow_state(run_id, "artifact-quiz")
        count_result = await session.execute(
            select(ArtifactWorkflow).where(ArtifactWorkflow.run_id == run_id),
        )

        assert persisted == failed
        assert len(list(count_result.scalars().all())) == 1
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession, run_id: RunId) -> None:
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-artifact-workflow"),
        raw_request="Teach fractions",
        class_info={"grade": 5, "subject": "math"},
    ))


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


def _state(
    run_id: RunId,
    *,
    status: ArtifactWorkflowStatus,
    attempts: int,
    last_error: str | None,
) -> ArtifactWorkflowState:
    return ArtifactWorkflowState(
        workflow_id="workflow-quiz",
        run_id=run_id,
        artifact_id="artifact-quiz",
        artifact_type="quiz",
        status=status,
        attempts=attempts,
        contract_revision_id=1,
        research_guidance_id="guidance-quiz",
        validation_status="pending",
        judge_status="pending",
        snapshot_refs=[],
        last_error=last_error,
    )
