from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.pipeline_v2_job_store import PipelineV2JobStore, RunJobCreate
from services.gateway.pipeline_v2_models import RunJob, RunJobKind, RunJobStatus
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
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
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Pipeline V2 run_jobs table is not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestPipelineV2JobStoreLeases:
    async def test_claim_next_marks_oldest_pending_job_running(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        first = await _enqueue_job(session, run_id, RunJobKind.START)
        await _enqueue_job(session, run_id, RunJobKind.RESUME)

        claimed = await PipelineV2JobStore(session).claim_next(
            lease_owner="worker-a",
            lease_seconds=30,
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        await session.commit()

        assert claimed is not None
        assert claimed.job_id == first.job_id
        assert claimed.status is RunJobStatus.RUNNING
        assert claimed.attempts == 1
        await _delete_run(session, run_id)

    async def test_claim_next_does_not_claim_unexpired_running_job(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        first = await _enqueue_job(session, run_id, RunJobKind.START)
        second = await _enqueue_job(session, run_id, RunJobKind.RESUME)
        store = PipelineV2JobStore(session)
        now = datetime(2026, 1, 1, tzinfo=UTC)
        await store.claim_next("worker-a", lease_seconds=30, now=now)

        claimed = await store.claim_next("worker-b", lease_seconds=30, now=now)
        await session.commit()

        assert claimed is not None
        assert claimed.job_id == second.job_id
        assert claimed.job_id != first.job_id
        await _delete_run(session, run_id)

    async def test_claim_next_reclaims_expired_running_job(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        first = await _enqueue_job(session, run_id, RunJobKind.START)
        store = PipelineV2JobStore(session)
        now = datetime(2026, 1, 1, tzinfo=UTC)
        await store.claim_next("worker-a", lease_seconds=1, now=now)

        reclaimed = await store.claim_next(
            "worker-b",
            lease_seconds=30,
            now=now + timedelta(seconds=2),
        )
        await session.commit()

        assert reclaimed is not None
        assert reclaimed.job_id == first.job_id
        assert reclaimed.attempts == 2
        await _delete_run(session, run_id)

    async def test_completed_job_is_not_reclaimed_after_lease_expiry(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        claimed = await _claim_one(session, run_id)
        store = PipelineV2JobStore(session)

        completed = await store.mark_completed(claimed.job_id)
        reclaimed = await store.claim_next(
            "worker-b",
            lease_seconds=30,
            now=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=1),
        )
        await session.commit()

        assert completed is True
        assert reclaimed is None
        await _delete_run(session, run_id)

    async def test_mark_failed_clears_running_lease(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        claimed = await _claim_one(session, run_id)

        failed = await PipelineV2JobStore(session).mark_failed(claimed.job_id)
        statement = select(RunJob).where(RunJob.job_id == claimed.job_id)
        result = await session.execute(statement)
        job = result.scalar_one()
        await session.commit()

        assert failed is True
        assert job.status is RunJobStatus.FAILED
        assert job.lease_owner is None
        assert job.lease_expires_at is None
        await _delete_run(session, run_id)

    async def test_cancel_run_jobs_cancels_pending_and_running_jobs(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        running_source = await _enqueue_job(session, run_id, RunJobKind.START)
        pending = await _enqueue_job(session, run_id, RunJobKind.RESUME)
        running = await PipelineV2JobStore(session).claim_next(
            lease_owner="worker-a",
            lease_seconds=30,
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )

        cancelled_count = await PipelineV2JobStore(session).cancel_run_jobs(run_id)
        statement = select(RunJob).where(RunJob.run_id == run_id).order_by(RunJob.created_at)
        result = await session.execute(statement)
        jobs = result.scalars().all()
        await session.commit()

        assert running is not None
        assert cancelled_count == 2
        assert [job.job_id for job in jobs] == [running_source.job_id, pending.job_id]
        assert {job.status for job in jobs} == {RunJobStatus.CANCELLED}
        assert all(job.lease_owner is None for job in jobs)
        assert all(job.lease_expires_at is None for job in jobs)
        await _delete_run(session, run_id)

    async def test_cancel_run_jobs_includes_queued_jobs(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        future = datetime(2099, 1, 1, tzinfo=UTC)
        queued = await PipelineV2JobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "cancel-queued-test"},
            eligible_at=future,
        ))
        pending = await _enqueue_job(session, run_id, RunJobKind.RESUME)
        await session.flush()

        cancelled_count = await PipelineV2JobStore(session).cancel_run_jobs(run_id)
        queued_status = await _get_job_status(session, queued.job_id)
        pending_status = await _get_job_status(session, pending.job_id)
        await session.commit()

        assert cancelled_count == 2
        assert queued_status is RunJobStatus.CANCELLED
        assert pending_status is RunJobStatus.CANCELLED
        await _delete_run(session, run_id)

    async def test_promote_eligible_moves_queued_to_pending(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        now = datetime(2026, 6, 1, tzinfo=UTC)
        eligible = now - timedelta(seconds=1)
        job = await PipelineV2JobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "promote-test"},
            eligible_at=eligible,
        ))
        await session.flush()

        promoted = await PipelineV2JobStore(session).promote_eligible(
            limit=5,
            now=now,
        )
        status = await _get_job_status(session, job.job_id)
        await session.commit()

        assert job.job_id in promoted
        assert status is RunJobStatus.PENDING
        await _delete_run(session, run_id)

    async def test_promote_eligible_skips_ineligible_jobs(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        future = datetime(2099, 1, 1, tzinfo=UTC)
        job = await PipelineV2JobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "promote-ineligible-test"},
            eligible_at=future,
        ))
        await session.flush()

        promoted = await PipelineV2JobStore(session).promote_eligible(
            limit=5,
            now=datetime(2026, 6, 1, tzinfo=UTC),
        )
        status = await _get_job_status(session, job.job_id)
        await session.commit()

        assert job.job_id not in promoted
        assert status is RunJobStatus.QUEUED
        await _delete_run(session, run_id)

    async def test_promote_eligible_respects_limit(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        now = datetime(2026, 6, 1, tzinfo=UTC)
        eligible = now - timedelta(seconds=1)
        jobs = []
        for _ in range(3):
            job = await PipelineV2JobStore(session).enqueue(RunJobCreate(
                job_id=f"job-{uuid4()}",
                run_id=run_id,
                kind=RunJobKind.START,
                idempotency_key=f"idem-{uuid4()}",
                payload={"source": "promote-limit-test"},
                eligible_at=eligible,
            ))
            jobs.append(job)
        await session.flush()

        promoted = await PipelineV2JobStore(session).promote_eligible(
            limit=2,
            now=now,
        )
        await session.commit()

        assert len(promoted) == 2
        statuses = []
        for job in jobs:
            statuses.append(await _get_job_status(session, job.job_id))
        assert statuses.count(RunJobStatus.PENDING) == 2
        assert statuses.count(RunJobStatus.QUEUED) == 1
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach job leases",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session: AsyncSession, run_id: RunId, kind: RunJobKind):
    return await PipelineV2JobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=kind,
        idempotency_key=f"idem-{uuid4()}",
        payload={"source": "lease-test"},
    ))


async def _claim_one(session: AsyncSession, run_id: RunId):
    await _enqueue_job(session, run_id, RunJobKind.START)
    claimed = await PipelineV2JobStore(session).claim_next(
        lease_owner="worker-a",
        lease_seconds=30,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert claimed is not None
    return claimed


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def _get_job_status(session: AsyncSession, job_id: str) -> RunJobStatus:
    statement = select(RunJob.status).where(RunJob.job_id == job_id)
    result = await session.execute(statement)
    return result.scalar_one()
