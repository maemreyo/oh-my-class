"""#124: a permanent/unclassified error dead-letters a job immediately (0 retries) -- never requeued, never left running."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.llm_client.errors import BadPromptError, PermanentProviderError
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
        pytest.skip(f"Postgres is unavailable for permanent failure tests: {exc}")
    finally:
        await engine.dispose()


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-perm-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-perm-test"),
        raw_request="Teach permanent failure",
        class_info={"grade": 6},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session, run_id: RunId):
    return await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-perm-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-perm-{uuid4()}",
        payload={"initial_state": {"run_id": run_id}},
    ))


async def _job_row(session, job_id: str) -> RunJob:
    result = await session.execute(select(RunJob).where(RunJob.job_id == job_id))
    return result.scalar_one()


async def test_permanent_provider_error_dead_letters_job_immediately(session) -> None:
    """PermanentProviderError must result in DEAD_LETTER, not QUEUED, with zero retries."""
    run_id = await _create_run(session)
    try:
        job = await _enqueue_job(session, run_id)

        class _PermanentErrorExecutor:
            async def run_start_job(self, _job):
                raise PermanentProviderError("bad schema validation response")

            async def run_resume_job(self, _job):
                raise PermanentProviderError("bad schema validation response")

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(worker_id="test-worker-perm", lease_seconds=30)
        worker = TeachingPackWorker(store, _PermanentErrorExecutor(), config)

        did_work = await worker.run_one()
        await session.commit()

        row = await _job_row(session, job.job_id)
        assert did_work is True
        assert row.status == RunJobStatus.DEAD_LETTER, f"Expected DEAD_LETTER, got {row.status}"
        assert row.attempts == 1, "permanent errors dead-letter with zero retries"
        assert row.error_classification == "permanent"
        assert row.last_error is not None and "bad schema validation" in row.last_error
    finally:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


async def test_bad_prompt_error_dead_letters_job_immediately(session) -> None:
    """BadPromptError (subclass of PermanentProviderError) must dead-letter, zero retries."""
    run_id = await _create_run(session)
    try:
        job = await _enqueue_job(session, run_id)

        class _BadPromptExecutor:
            async def run_start_job(self, _job):
                raise BadPromptError("HTTP 400: prompt rejected")

            async def run_resume_job(self, _job):
                raise BadPromptError("HTTP 400: prompt rejected")

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(worker_id="test-worker-bad", lease_seconds=30)
        worker = TeachingPackWorker(store, _BadPromptExecutor(), config)

        did_work = await worker.run_one()
        await session.commit()

        row = await _job_row(session, job.job_id)
        assert did_work is True
        assert row.status == RunJobStatus.DEAD_LETTER, f"Expected DEAD_LETTER, got {row.status}"
        assert row.error_classification == "permanent"
    finally:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


async def test_generic_exception_dead_letters_job(session) -> None:
    """Any non-TransientProviderError exception must dead-letter, not silently fail closed elsewhere."""
    run_id = await _create_run(session)
    try:
        job = await _enqueue_job(session, run_id)

        class _GenericErrorExecutor:
            async def run_start_job(self, _job):
                raise RuntimeError("unexpected crash")

            async def run_resume_job(self, _job):
                raise RuntimeError("unexpected crash")

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(worker_id="test-worker-generic", lease_seconds=30)
        worker = TeachingPackWorker(store, _GenericErrorExecutor(), config)

        await worker.run_one()
        await session.commit()

        row = await _job_row(session, job.job_id)
        assert row.status == RunJobStatus.DEAD_LETTER, f"Expected DEAD_LETTER, got {row.status}"
        assert row.error_classification == "permanent"
    finally:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


async def test_transient_error_retries_then_dead_letters_after_ceiling(session) -> None:
    """A TransientProviderError retries with backoff up to max_transient_attempts, then dead-letters."""
    from packages.llm_client.errors import ProviderTimeoutError

    run_id = await _create_run(session)
    try:
        job = await _enqueue_job(session, run_id)

        class _TransientErrorExecutor:
            async def run_start_job(self, _job):
                raise ProviderTimeoutError("provider timed out")

            async def run_resume_job(self, _job):
                raise ProviderTimeoutError("provider timed out")

        store = TeachingPackJobStore(session)
        config = TeachingPackWorkerConfig(worker_id="test-worker-transient", lease_seconds=30, max_transient_attempts=2)
        worker = TeachingPackWorker(store, _TransientErrorExecutor(), config)

        # First failure: attempts == 1 < ceiling (2) -> requeued, not dead-lettered.
        await worker.run_one()
        await session.commit()
        row = await _job_row(session, job.job_id)
        assert row.status == RunJobStatus.QUEUED
        assert row.attempts == 1

        # Second failure: attempts == 2 >= ceiling (2) -> dead-lettered.
        await worker.run_one(now=row.eligible_at)
        await session.commit()
        row = await _job_row(session, job.job_id)
        assert row.status == RunJobStatus.DEAD_LETTER
        assert row.attempts == 2
        assert row.error_classification == "transient_exhausted"
    finally:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
