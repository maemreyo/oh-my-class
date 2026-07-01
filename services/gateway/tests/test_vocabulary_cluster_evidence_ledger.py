from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.vocabulary_cluster_workflow import VocabularyClusterEvidenceEntry, VocabularyClusterWorkflow
from services.gateway.models import Base, Run
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
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
            if "public.vocabulary_cluster_evidence" not in tables:
                pytest.skip("Vocabulary cluster evidence table is not present")
    except (OSError, OperationalError) as exc:
        pytest.skip(f"local Postgres unavailable: {exc}")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestVocabularyClusterEvidenceLedger:
    async def test_evidence_entries_append_in_sequence_order(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)
        store = VocabularyClusterWorkflowStore(session)
        await store.upsert_workflow(_workflow(run_id))

        first = await store.append_evidence(_entry(run_id, sequence=1, event_type="normalized_input"))
        second = await store.append_evidence(_entry(run_id, sequence=2, event_type="grounding_sources"))
        await session.commit()

        entries = await store.list_evidence(run_id, "cluster-1")

        assert [first.sequence, second.sequence] == [1, 2]
        assert [entry.event_type for entry in entries] == ["normalized_input", "grounding_sources"]
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession, run_id: RunId) -> None:
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-vocabulary-evidence"),
        raw_request="Teach vocabulary clusters",
        class_info={"grade": 8, "subject": "english"},
    ))


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


def _workflow(run_id: RunId) -> VocabularyClusterWorkflow:
    return VocabularyClusterWorkflow(
        workflow_id="workflow-cluster-1",
        cluster_id="cluster-1",
        run_id=run_id,
        normalized_input=("travel", "journey"),
        raw_input_span="travel / journey",
        status="queued",
        attempts=0,
        review_status="pending",
        export_refs={},
        snapshot_hash="c" * 64,
        last_error=None,
    )


def _entry(run_id: RunId, *, sequence: int, event_type: str) -> VocabularyClusterEvidenceEntry:
    return VocabularyClusterEvidenceEntry(
        evidence_id=f"evidence-{sequence}",
        workflow_id="workflow-cluster-1",
        cluster_id="cluster-1",
        run_id=run_id,
        sequence=sequence,
        event_type=event_type,
        payload={"sequence": sequence},
    )
