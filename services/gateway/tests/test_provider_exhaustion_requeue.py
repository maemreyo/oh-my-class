"""Test that a FreeTierExhaustedError requeues the job (not FAILED) and can be reclaimed."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.llm_client.errors import FreeTierExhaustedError
from services.gateway.models import Base, Run
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJob, RunJobKind, RunJobStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.teaching_pack_worker import TeachingPackWorker, TeachingPackWorkerConfig

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            existing_tables = await connection.run_sync(lambda _connection: set(Base.metadata.tables))
            if "public.run_jobs" not in existing_tables:
                pytest.skip("Teaching Pack run_jobs table is not present")
        async with session_factory() as database_session:
            yield database_session
            await database_session.rollback()
    except (OSError, SQLAlchemyError) as exc:
        pytest.skip(f"Postgres is unavailable for provider requeue tests: {exc}")
    finally:
        await engine.dispose()


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-prov-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-prov-test"),
        raw_request="Teach resilience",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session, run_id: RunId):
    return await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-prov-{uuid4()}",
        payload={"initial_state": {"run_id": run_id}},
    ))


async def test_free_tier_exhausted_requeues_not_fails(session) -> None:
    """FreeTierExhaustedError must requeue the job (QUEUED), never FAILED."""
    run_id = await _create_run(session)
    try:
        await _enqueue_job(session, run_id)

        class _ErrorExecutor:
            async def run_start_job(self, _job):
                raise FreeTierExhaustedError("free tier quota", retry_after_seconds=120)

            async def run_resume_job(self, _job):
                raise FreeTierExhaustedError("free tier quota", retry_after_seconds=120)

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(
            worker_id="test-worker",
            lease_seconds=30,
        )
        worker = TeachingPackWorker(store, _ErrorExecutor(), config)

        start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        did_work = await worker.run_one(now=start)
        await session.commit()

        jobs = await session.execute(select(RunJob).where(RunJob.run_id == run_id))
        job = jobs.scalar_one()

        assert did_work is True
        assert job.status == RunJobStatus.QUEUED, f"Expected QUEUED, got {job.status}"
        assert job.eligible_at is not None
        assert job.eligible_at > start
    finally:
        from sqlalchemy import delete
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


async def test_free_tier_exhausted_eligible_at_in_future(session) -> None:
    """The eligible_at is set to now + retry_after_seconds."""
    run_id = await _create_run(session)
    try:
        await _enqueue_job(session, run_id)

        class _ErrorExecutor:
            async def run_start_job(self, _job):
                raise FreeTierExhaustedError("quota", retry_after_seconds=300)

            async def run_resume_job(self, _job):
                raise FreeTierExhaustedError("quota", retry_after_seconds=300)

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(worker_id="test-worker-2", lease_seconds=30)
        worker = TeachingPackWorker(store, _ErrorExecutor(), config)

        start = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        await worker.run_one(now=start)
        await session.commit()

        jobs = await session.execute(select(RunJob).where(RunJob.run_id == run_id))
        job = jobs.scalar_one()

        expected_eligible = start + timedelta(seconds=300)
        assert job.eligible_at is not None
        # Allow 1 second of slop
        assert abs((job.eligible_at - expected_eligible).total_seconds()) < 1
    finally:
        from sqlalchemy import delete
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


async def test_requeued_job_is_reclaimed_after_eligible_at(session) -> None:
    """After eligible_at passes, claim_next picks up the requeued job."""
    run_id = await _create_run(session)
    try:
        await _enqueue_job(session, run_id)

        class _ErrorExecutor:
            async def run_start_job(self, _job):
                raise FreeTierExhaustedError("quota", retry_after_seconds=60)

            async def run_resume_job(self, _job):
                raise FreeTierExhaustedError("quota", retry_after_seconds=60)

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(worker_id="test-worker-3", lease_seconds=30)
        worker = TeachingPackWorker(store, _ErrorExecutor(), config)

        start = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        await worker.run_one(now=start)
        await session.commit()

        # Attempt to claim before eligible_at — should fail
        before_eligible = start + timedelta(seconds=30)
        job_before = await store.claim_next("worker-x", lease_seconds=30, now=before_eligible)
        assert job_before is None or job_before.run_id != run_id, (
            "Job should not be claimable before eligible_at"
        )

        # Attempt to claim after eligible_at — should succeed (uses promote_eligible path)
        after_eligible = start + timedelta(seconds=120)
        # First promote eligible jobs
        await store.promote_eligible(limit=10, now=after_eligible)
        job_after = await store.claim_next("worker-y", lease_seconds=30, now=after_eligible)

        if job_before is not None and job_before.run_id == run_id:
            pass  # already asserted above
        else:
            assert job_after is not None, "Job should be claimable after eligible_at"

        await session.commit()
    finally:
        from sqlalchemy import delete
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
