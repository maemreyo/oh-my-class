from __future__ import annotations

from uuid import uuid4

import anyio
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_job_store import RunJobCreate, RunJobRead, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJobKind
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

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


async def test_two_workers_claim_disjoint_jobs(session_factory) -> None:
    async with session_factory() as session:
        run_id = await _create_run(session)
        await _enqueue_job(session, run_id)
        await _enqueue_job(session, run_id)
        await session.commit()

    claimed: list[RunJobRead] = []

    async def claim(worker_id: str) -> None:
        async with session_factory() as session:
            job = await TeachingPackJobStore(session).claim_next(worker_id, lease_seconds=30)
            await session.commit()
            assert job is not None
            claimed.append(job)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(claim, "worker-a")
        task_group.start_soon(claim, "worker-b")

    assert len({job.job_id for job in claimed}) == 2


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-multi-worker"),
        raw_request="Teach multi-worker",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session, run_id: RunId) -> None:
    await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-{uuid4()}",
        payload={"initial_state": {"run_id": run_id}},
    ))
