from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_executor import TeachingPackResumeJob, TeachingPackStartJob
from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobCreate
from services.gateway.teaching_pack_models import RunJob, RunJobKind, RunJobStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId
from services.gateway.teaching_pack_worker import TeachingPackWorker, TeachingPackWorkerConfig

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
            pytest.skip("Teaching Pack run_jobs table is not present")
    async with session_factory() as database_session:
        await _delete_test_runs(database_session)
        await database_session.commit()
        yield database_session
        await database_session.rollback()
        await _delete_test_runs(database_session)
        await database_session.commit()
    await engine.dispose()


@dataclass(slots=True)
class RecordingExecutor:
    start_jobs: list[TeachingPackStartJob] = field(default_factory=list)
    resume_jobs: list[TeachingPackResumeJob] = field(default_factory=list)
    fail: bool = False
    fail_once: bool = False

    async def run_start_job(self, job: TeachingPackStartJob) -> None:
        self.start_jobs.append(job)
        if self.fail or self.fail_once:
            self.fail_once = False
            raise RuntimeError("worker graph failed")

    async def run_resume_job(self, job: TeachingPackResumeJob) -> None:
        self.resume_jobs.append(job)
        if self.fail or self.fail_once:
            self.fail_once = False
            raise RuntimeError("worker graph failed")


class TestTeachingPackWorker:
    async def test_run_one_returns_false_when_no_job(self, session: AsyncSession) -> None:
        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one()

        assert did_work is False
        assert executor.start_jobs == []
        assert executor.resume_jobs == []

    async def test_run_one_executes_start_job_and_marks_completed(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        job = await _enqueue_job(
            session,
            run_id,
            RunJobKind.START,
            {"initial_state": {"run_id": run_id, "raw_request": "Teach worker"}},
        )
        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one()
        status = await _job_status(session, job.job_id)

        assert did_work is True
        assert executor.start_jobs == [TeachingPackStartJob(
            run_id=run_id,
            initial_state={"run_id": run_id, "raw_request": "Teach worker"},
        )]
        assert status is RunJobStatus.COMPLETED
        await _delete_run(session, run_id)

    async def test_run_one_passes_contract_to_start_job_initial_state(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        contract = {"run_id": run_id, "topic": "Fractions"}
        await _enqueue_job(
            session,
            run_id,
            RunJobKind.START,
            {"contract": contract},
        )
        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one()

        assert did_work is True
        assert executor.start_jobs == [TeachingPackStartJob(
            run_id=run_id,
            initial_state={"run_id": run_id, "contract": contract},
        )]
        await _delete_run(session, run_id)

    async def test_run_one_executes_resume_job_and_marks_completed(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        job = await _enqueue_job(
            session,
            run_id,
            RunJobKind.RESUME,
            {
                "response_id": "response-1",
                "resume_payload": {"action": "approve"},
            },
        )
        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one()
        status = await _job_status(session, job.job_id)

        assert did_work is True
        assert executor.resume_jobs == [TeachingPackResumeJob(
            run_id=run_id,
            gate_response_id="response-1",
            resume_payload={"action": "approve"},
        )]
        assert status is RunJobStatus.COMPLETED
        await _delete_run(session, run_id)

    async def test_run_one_marks_job_failed_when_executor_raises(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        job = await _enqueue_job(
            session,
            run_id,
            RunJobKind.START,
            {"initial_state": {"run_id": run_id}},
        )
        executor = RecordingExecutor(fail=True)
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one()
        status = await _job_status(session, job.job_id)

        assert did_work is True
        assert status is RunJobStatus.FAILED
        await _delete_run(session, run_id)

    async def test_run_loop_drains_jobs_until_idle(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        start_job = await _enqueue_job(
            session,
            run_id,
            RunJobKind.START,
            {"initial_state": {"run_id": run_id, "raw_request": "Teach worker"}},
        )
        resume_job = await _enqueue_job(
            session,
            run_id,
            RunJobKind.RESUME,
            {"response_id": "response-1", "resume_payload": {"action": "approve"}},
        )
        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        completed = await worker.run_loop(max_iterations=3)
        start_status = await _job_status(session, start_job.job_id)
        resume_status = await _job_status(session, resume_job.job_id)

        assert completed == 2
        assert len(executor.start_jobs) == 1
        assert len(executor.resume_jobs) == 1
        assert start_status is RunJobStatus.COMPLETED
        assert resume_status is RunJobStatus.COMPLETED
        await _delete_run(session, run_id)

    async def test_run_one_skips_queued_ineligible_jobs(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        future = datetime(2099, 1, 1, tzinfo=UTC)
        await TeachingPackJobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"initial_state": {"run_id": run_id}},
            eligible_at=future,
        ))
        await session.flush()

        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one(now=datetime(2026, 1, 1, tzinfo=UTC))

        assert did_work is False
        assert executor.start_jobs == []
        await _delete_run(session, run_id)

    async def test_run_one_claims_eligible_queued_job(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        now = datetime(2026, 6, 1, tzinfo=UTC)
        eligible = now - timedelta(seconds=1)
        job = await TeachingPackJobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"initial_state": {"run_id": run_id, "raw_request": "Queued job"}},
            eligible_at=eligible,
        ))
        await session.flush()

        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(worker_id="worker-a", lease_seconds=30, idle_sleep_seconds=0),
        )

        did_work = await worker.run_one(now=now)
        status = await _job_status(session, job.job_id)

        assert did_work is True
        assert len(executor.start_jobs) == 1
        assert status is RunJobStatus.COMPLETED
        await _delete_run(session, run_id)

    async def test_worker_promotes_eligible_queued_after_completion(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        now = datetime(2026, 6, 1, tzinfo=UTC)
        eligible = now - timedelta(seconds=1)

        _pending_job = await _enqueue_job(
            session,
            run_id,
            RunJobKind.START,
            {"initial_state": {"run_id": run_id, "raw_request": "First"}},
        )
        queued_job = await TeachingPackJobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"initial_state": {"run_id": run_id, "raw_request": "Second"}},
            eligible_at=eligible,
        ))
        await session.flush()

        executor = RecordingExecutor()
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(
                worker_id="worker-a",
                lease_seconds=30,
                idle_sleep_seconds=0,
                promote_batch_size=5,
            ),
        )

        completed = await worker.run_loop(max_iterations=3)
        queued_status = await _job_status(session, queued_job.job_id)

        assert completed == 2
        assert len(executor.start_jobs) == 2
        assert queued_status is RunJobStatus.COMPLETED
        await _delete_run(session, run_id)

    async def test_cancel_run_jobs_cancels_queued_jobs(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        future = datetime(2099, 1, 1, tzinfo=UTC)
        queued = await TeachingPackJobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "cancel-test"},
            eligible_at=future,
        ))
        pending = await _enqueue_job(
            session,
            run_id,
            RunJobKind.RESUME,
            {"response_id": "r-1"},
        )
        await session.flush()

        cancelled = await TeachingPackJobStore(session).cancel_run_jobs(run_id)
        queued_status = await _job_status(session, queued.job_id)
        pending_status = await _job_status(session, pending.job_id)

        assert cancelled == 2
        assert queued_status is RunJobStatus.CANCELLED
        assert pending_status is RunJobStatus.CANCELLED
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-worker"),
        raw_request="Teach worker",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(
    session: AsyncSession,
    run_id: RunId,
    kind: RunJobKind,
    payload: JsonObject,
):
    return await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=kind,
        idempotency_key=f"idem-{uuid4()}",
        payload=payload,
    ))


async def _job_status(session: AsyncSession, job_id: str) -> RunJobStatus:
    statement = select(RunJob.status).where(RunJob.job_id == job_id)
    result = await session.execute(statement)
    return result.scalar_one()


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def _delete_test_runs(session: AsyncSession) -> None:
    await session.execute(delete(Run).where(Run.run_id.like("test-%")))
