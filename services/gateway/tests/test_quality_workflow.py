from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.quality import ArtifactQualityReport, QualityFailureClass, QualityIssue
from services.gateway.models import Base, Run
from services.gateway.pipeline_v2_models import RunEvent
from services.gateway.pipeline_v2_snapshot_models import ArtifactSnapshot
from services.gateway.pipeline_v2_snapshot_store import (
    ArtifactSnapshotCreate,
    PipelineV2SnapshotStore,
)
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import JsonObject, RunId, TeacherId
from services.gateway.quality_workflow import (
    evaluate_export_readiness,
    write_artifact_quality_event,
)

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


async def test_quality_event_payload_is_compact(session: AsyncSession) -> None:
    run_id = RunId(f"test-{uuid4()}")
    await _create_run(session, run_id)
    report = ArtifactQualityReport(
        artifact_id="quiz-1",
        artifact_type="quiz",
        passed=False,
        issues=[QualityIssue(
            failure_class=QualityFailureClass.ANSWER_KEY_LEAKAGE,
            location="sections[0]",
            message="answer leaked",
        )],
    )

    event = await write_artifact_quality_event(session, run_id, report)
    await session.commit()

    assert event.event_name == "pipeline_v2.quality.artifact_failed"
    assert event.payload == {
        "artifact_id": "quiz-1",
        "artifact_type": "quiz",
        "passed": False,
        "issues": [{
            "failure_class": "answer_key_leakage",
            "location": "sections[0]",
            "message": "answer leaked",
            "hard_block": True,
        }],
    }
    await _delete_run(session, run_id)


async def test_export_readiness_uses_approved_snapshots_and_writes_event(
    session: AsyncSession,
) -> None:
    run_id = RunId(f"test-{uuid4()}")
    await _create_run(session, run_id)
    await PipelineV2SnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id="snap-lesson",
        run_id=run_id,
        artifact_id="lesson-1",
        artifact_type="lesson",
        content_json={"title": "Lesson"},
        rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
        renderer_version="renderer@test",
    ))
    await PipelineV2SnapshotStore(session).approve_snapshots(run_id, ["snap-lesson"])

    report = await evaluate_export_readiness(session, run_id, ("lesson", "quiz"))
    stored_event = await _latest_event(session, run_id)

    assert report.passed is False
    assert report.approved_snapshot_ids == ["snap-lesson"]
    assert stored_event is not None
    assert stored_event["approved_snapshot_ids"] == ["snap-lesson"]
    assert "rendered_html" not in str(stored_event)
    await _delete_run(session, run_id)


async def _create_run(session: AsyncSession, run_id: RunId) -> None:
    await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-quality"),
        raw_request="Teach quality gates",
        class_info={"grade": 5},
    ))


async def _latest_event(session: AsyncSession, run_id: RunId) -> JsonObject | None:
    result = await session.execute(
        select(RunEvent.payload)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.sequence.desc()),
    )
    return result.scalar_one()


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id))
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()
