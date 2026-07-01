from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus
from services.gateway.release_evidence import ReleaseEvidence, generate_evidence, render_evidence_markdown
from services.gateway.teaching_pack_models import RunEvent, TeachingPackEventVisibility
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
        existing = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.runs" not in existing:
            pytest.skip("Teaching Pack tables are not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestReleaseEvidenceExports:
    async def test_generate_evidence_includes_exported_files_from_completion_event(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = RunId(f"ev-export-{uuid4()}")
        export_path = f".scratch/pipeline-v2/artifacts/exports/{run_id}/snap.html"
        session.add(Run(
            run_id=run_id,
            teacher_id=TeacherId("teacher-export"),
            status=RunStatus.COMPLETED,
            current_step=13,
            raw_request="Test export evidence",
            class_info={"grade": 5},
        ))
        session.add(RunEvent(
            run_id=run_id,
            sequence=1,
            event_name="teaching_pack.run.completed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"exported_files": [export_path]},
        ))
        await session.flush()

        evidence = await generate_evidence(run_id, session)

        assert evidence.export_files == [export_path]
        assert export_path in render_evidence_markdown(evidence)
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    def test_render_markdown_includes_artifact_send_rollout_receipts(self) -> None:
        evidence = ReleaseEvidence(
            run_id="run-send-rollout",
            teacher_id_hash="teacherhash1234",
            status="completed",
            event_sequence=[
                {
                    "sequence": 1,
                    "event_name": "teaching_pack.artifact_send.rollout_evidence",
                    "stage": "artifact_workflow",
                    "created_at": "2026-07-01T00:00:00+00:00",
                    "payload": {
                        "scenario": "flag-on happy path",
                        "status": "pass",
                        "command": "uv run pytest tests/e2e/test_artifact_send_fanout_flow.py -q",
                        "artifacts": ["lesson-1", "quiz-1", "recap-1"],
                    },
                },
            ],
        )

        markdown = render_evidence_markdown(evidence)

        assert "## Artifact Send rollout evidence" in markdown
        assert "[PASS] flag-on happy path" in markdown
        assert "test_artifact_send_fanout_flow.py" in markdown
        assert "lesson-1, quiz-1, recap-1" in markdown

    def test_render_markdown_includes_vocabulary_batch_rollout_receipts(self) -> None:
        evidence = ReleaseEvidence(
            run_id="run-vocabulary-rollout",
            teacher_id_hash="teacherhash5678",
            status="completed",
            event_sequence=[
                {
                    "sequence": 1,
                    "event_name": "teaching_pack.vocabulary_batch.rollout_evidence",
                    "stage": "artifact_workflow",
                    "created_at": "2026-07-01T00:00:00+00:00",
                    "payload": {
                        "scenario": "20-cluster happy path with partial review",
                        "status": "pass",
                        "command": "uv run pytest tests/e2e/test_vocabulary_batch_flow.py -q",
                        "cluster_counts": {"passed": 18, "needs_review": 1, "failed": 1},
                        "exports": ["exports/run-vocabulary/vocabulary-batch.zip"],
                    },
                },
            ],
            export_files=["exports/run-vocabulary/vocabulary-batch.zip"],
        )

        markdown = render_evidence_markdown(evidence)

        assert "## Vocabulary batch rollout evidence" in markdown
        assert "[PASS] 20-cluster happy path with partial review" in markdown
        assert "test_vocabulary_batch_flow.py" in markdown
        assert "failed=1, needs_review=1, passed=18" in markdown
        assert "exports/run-vocabulary/vocabulary-batch.zip" in markdown
