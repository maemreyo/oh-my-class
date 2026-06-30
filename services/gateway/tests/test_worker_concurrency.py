from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_executor import TeachingPackResumeJob, TeachingPackStartJob
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJobKind
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.teaching_pack_worker import TeachingPackWorkerConfig, run_worker_batch

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session_factory():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _connection: set(Base.metadata.tables))
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack run_jobs table is not present")
    async with factory() as session:
        await session.execute(delete(Run).where(Run.run_id.like("test-%")))
        await session.commit()
    yield factory
    async with factory() as session:
        await session.execute(delete(Run).where(Run.run_id.like("test-%")))
        await session.commit()
    await engine.dispose()


@dataclass(slots=True)
class BlockingExecutor:
    entered: int = 0
    max_entered: int = 0
    release: anyio.Event = field(default_factory=anyio.Event)

    async def run_start_job(self, job: TeachingPackStartJob) -> None:
        _ = job
        self.entered += 1
        self.max_entered = max(self.max_entered, self.entered)
        await self.release.wait()
        self.entered -= 1

    async def run_resume_job(self, job: TeachingPackResumeJob) -> None:
        _ = job
        await self.run_start_job(TeachingPackStartJob(run_id=job.run_id, initial_state={}))


async def test_worker_batch_runs_up_to_configured_concurrency(session_factory) -> None:
    async with session_factory() as session:
        run_id = await _create_run(session)
        for index in range(5):
            await _enqueue_job(session, run_id, index)
        await session.commit()

    executor = BlockingExecutor()
    config = TeachingPackWorkerConfig(
        worker_id="worker-a",
        lease_seconds=30,
        idle_sleep_seconds=0,
        worker_concurrency=4,
    )

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(run_worker_batch, session_factory, lambda _session: executor, config)
        while executor.max_entered < 4:
            await anyio.sleep(0.01)
        assert executor.entered == 4
        executor.release.set()


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-concurrency"),
        raw_request="Teach concurrency",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session, run_id: RunId, index: int) -> None:
    await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-{uuid4()}",
        payload={"initial_state": {"run_id": run_id, "index": index}},
    ))
