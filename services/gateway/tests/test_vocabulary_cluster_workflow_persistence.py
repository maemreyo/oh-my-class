from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.vocabulary_cluster_workflow import VocabularyClusterWorkflow
from services.gateway.models import Base, Run
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.vocabulary_cluster_models import VocabularyClusterWorkflowModel
from services.gateway.vocabulary_cluster_store import VocabularyClusterWorkflowStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
            if "public.vocabulary_cluster_workflows" not in tables:
                pytest.skip("Vocabulary cluster workflow table is not present")
    except (OSError, OperationalError) as exc:
        pytest.skip(f"local Postgres unavailable: {exc}")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestVocabularyClusterWorkflowPersistence:
    async def test_cluster_workflow_state_round_trips(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)
        state = _workflow(run_id, status="queued", attempts=0)
        store = VocabularyClusterWorkflowStore(session)

        await store.upsert_workflow(state)
        await session.commit()

        persisted = await store.get_workflow(run_id, "cluster-1")

        assert persisted == state
        await _delete_run(session, run_id)

    async def test_cluster_workflow_update_does_not_duplicate_record(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)
        queued = _workflow(run_id, status="queued", attempts=0)
        validating = _workflow(run_id, status="validating", attempts=1)
        store = VocabularyClusterWorkflowStore(session)

        await store.upsert_workflow(queued)
        await store.upsert_workflow(validating)
        await session.commit()

        persisted = await store.get_workflow(run_id, "cluster-1")
        count_result = await session.execute(
            select(VocabularyClusterWorkflowModel).where(VocabularyClusterWorkflowModel.run_id == run_id),
        )

        assert persisted == validating
        assert len(list(count_result.scalars().all())) == 1
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession, run_id: RunId) -> None:
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-vocabulary-cluster"),
        raw_request="Teach vocabulary clusters",
        class_info={"grade": 8, "subject": "english"},
    ))


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


def _workflow(run_id: RunId, *, status: str, attempts: int) -> VocabularyClusterWorkflow:
    return VocabularyClusterWorkflow(
        workflow_id="workflow-cluster-1",
        cluster_id="cluster-1",
        run_id=run_id,
        normalized_input=("travel", "journey"),
        raw_input_span="travel / journey",
        status=status,
        attempts=attempts,
        review_status="pending",
        export_refs={},
        snapshot_hash="b" * 64,
        last_error=None,
    )
