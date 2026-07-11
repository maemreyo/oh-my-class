"""#123 (OPS-10): kill-mid-job resilience test, against the real DB and the
real local MinIO -- not mocks.

Simulates the exact window at-least-once delivery exposes: a worker
completes `TeachingPackCompletionRecorder.persist_completion` (writes
exports + export_records + run_events + transitions the Run to COMPLETED)
but crashes before the RunJob row itself gets marked complete. The lease
expires, the sweeper reclaims the job, and the same completion logic runs
again (as it would on a real graph-checkpoint resume). Asserts: no
duplicate export object in MinIO, no duplicate export_records row, and the
run_events unique-sequence constraint holds without violation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from botocore.exceptions import EndpointConnectionError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus
from services.gateway.object_storage import build_s3_client, ensure_bucket_exists, object_storage_config_from_env
from services.gateway.recovery_sweeper import sweep_stuck_jobs
from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
from services.gateway.teaching_pack_export_store import TeachingPackExportStore
from services.gateway.teaching_pack_export_writer import ObjectStorageTeachingPackExportWriter
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunEvent, RunJob, RunJobKind, RunJobStatus
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate, TeachingPackSnapshotStore
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore, TeachingPackStatusTransition
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@dataclass(frozen=True, slots=True)
class RecordingRenderer:
    rendered_html: str = "<!DOCTYPE html><html><body>oh-my-class resilience recap</body></html>"
    calls: list[JsonObject] = field(default_factory=list)

    async def render(self, artifact: JsonObject) -> str:
        self.calls.append(artifact)
        return self.rendered_html


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


@pytest.fixture
def s3_client():
    config = object_storage_config_from_env()
    client = build_s3_client(config)
    try:
        ensure_bucket_exists(client, config.bucket)
    except EndpointConnectionError as exc:
        pytest.skip(f"MinIO is unavailable for resilience tests: {exc}")
    return client, config


def _completion_state(run_id: RunId, snapshot_id: str) -> JsonObject:
    return {
        "run_id": str(run_id),
        "exported_files": [f"exports/{run_id}/{snapshot_id}.html"],
        "approved_snapshot_ids": [snapshot_id],
        "rendered_snapshots": [{
            "snapshot_id": snapshot_id,
            "artifact_id": "artifact-1",
            "content_json": {"title": "Recap"},
        }],
    }


async def test_completion_survives_a_kill_between_side_effects_and_job_completion(
    session: AsyncSession, s3_client,
) -> None:
    client, config = s3_client
    # Content varies per invocation (unique_marker): ArtifactSnapshot.content_hash
    # has a *global* uniqueness constraint, so identical hardcoded content
    # across repeated runs of this test would collide with a prior run's
    # already-committed snapshot row (session.commit() makes it durable even
    # though the fixture's rollback() at teardown only undoes uncommitted work).
    run_id = RunId(f"test-resilience-{uuid4()}")
    snapshot_id = "snapshot-1"
    unique_marker = str(uuid4())

    try:
        run_store = TeachingPackRunStore(session)
        await run_store.create_run(TeachingPackRunCreate(
            run_id=run_id, teacher_id=TeacherId("teacher-resilience"),
            raw_request="Build a recap for resilience testing", class_info={"grade": 5},
        ))
        await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=snapshot_id, run_id=run_id, artifact_id="artifact-1", artifact_type="recap",
            content_json={"title": "Recap", "marker": unique_marker},
            rendered_html=f"<!DOCTYPE html><html><body>oh-my-class recap {unique_marker}</body></html>",
            renderer_version="test-renderer@1",
        ))
        job_store = TeachingPackJobStore(session)
        await job_store.enqueue(RunJobCreate(
            job_id=f"job-resilience-{uuid4()}", run_id=run_id, kind=RunJobKind.START,
            idempotency_key=f"idem-resilience-{uuid4()}", payload={"initial_state": {"run_id": run_id}},
        ))
        claimed = await job_store.claim_next(
            lease_owner="worker-a", lease_seconds=30, now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert claimed is not None
        await session.flush()
        await run_store.transition_status(TeachingPackStatusTransition(
            run_id=run_id, status=RunStatus.AWAITING_APPROVAL, stage=None, reason="test_setup",
        ))

        export_store = TeachingPackExportStore(session)
        renderer = RecordingRenderer()
        writer = ObjectStorageTeachingPackExportWriter(config=config, client=client, renderer=renderer)
        recorder = TeachingPackCompletionRecorder(run_store, export_writer=writer, export_store=export_store)
        state = _completion_state(run_id, snapshot_id)

        # First attempt: side effects run and commit, but the process "crashes"
        # before the job row itself is marked complete (worker.run_one's own
        # `mark_completed` call never happens -- we skip it deliberately).
        await recorder.persist_completion(run_id, state)
        await session.commit()

        # Simulate the crash: the lease is now expired, job is still RUNNING.
        job_row = (await session.execute(
            select(RunJob).where(RunJob.job_id == claimed.job_id),
        )).scalar_one()
        job_row.lease_expires_at = datetime(2020, 1, 1, tzinfo=UTC)
        await session.flush()
        await session.commit()

        recovered = await sweep_stuck_jobs(session, max_attempts=3)
        await session.commit()
        assert claimed.job_id in recovered
        reclaimed_row = (await session.execute(
            select(RunJob).where(RunJob.job_id == claimed.job_id),
        )).scalar_one()
        assert reclaimed_row.status == RunJobStatus.PENDING  # reclaimable, not dead-lettered

        # Re-claim and re-run the SAME completion logic (what a resumed graph
        # checkpoint would do) -- the retry this whole window exists to protect.
        reclaimed = await job_store.claim_next(
            lease_owner="worker-b", lease_seconds=30, now=datetime(2026, 1, 2, tzinfo=UTC),
        )
        assert reclaimed is not None
        await recorder.persist_completion(run_id, state)
        await job_store.mark_completed(reclaimed.job_id)
        await session.commit()

        # No duplicate export_records row for the same (snapshot_id, format).
        export_records = await export_store.list_exports(run_id)
        assert len(export_records) == 1

        # No duplicate object in MinIO -- overwrite-safe PUT, same key both times.
        key = f"exports/{run_id}/{snapshot_id}.html"
        stored = client.get_object(Bucket=config.bucket, Key=key)
        assert stored["Body"].read().decode("utf-8") == writer.renderer.rendered_html

        # run_events: two calls to persist_completion each wrote one
        # "teaching_pack.run.completed" event -- the (run_id, sequence)
        # unique constraint held without violation across the retry (each
        # write gets a fresh sequence; asserting membership, not exact
        # count, since events are append-only by design).
        events = (await session.execute(
            select(RunEvent).where(RunEvent.run_id == run_id),
        )).scalars().all()
        completed_events = [e for e in events if e.event_name == "teaching_pack.run.completed"]
        assert len(completed_events) >= 1
        assert len({e.sequence for e in events}) == len(events), "no two events share a sequence"

        # Final job/run state matches an uninterrupted run.
        final_job = (await session.execute(
            select(RunJob).where(RunJob.job_id == claimed.job_id),
        )).scalar_one()
        assert final_job.status == RunJobStatus.COMPLETED
    finally:
        await session.rollback()
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(RunEvent).where(RunEvent.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
