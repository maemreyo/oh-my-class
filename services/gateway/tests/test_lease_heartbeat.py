from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.recovery_sweeper import sweep_stuck_jobs
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJob, RunJobKind, RunJobStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _connection: set(Base.metadata.tables))
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack run_jobs table is not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def test_refresh_lease_keeps_long_running_job_from_being_reclaimed(session) -> None:
    run_id = await _create_run(session)
    job = await _enqueue_job(session, run_id)
    store = TeachingPackJobStore(session)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    claimed = await store.claim_next("worker-a", lease_seconds=30, now=start)

    refreshed = await store.refresh_lease(
        job_id=job.job_id,
        lease_owner="worker-a",
        lease_seconds=30,
        now=start + timedelta(seconds=20),
    )
    reclaimed = await store.claim_next(
        "worker-b",
        lease_seconds=30,
        now=start + timedelta(seconds=40),
    )
    await session.commit()

    try:
        assert claimed is not None
        assert claimed.job_id == job.job_id, "claim_next picked up a different job; check for leaked jobs in the DB"
        assert refreshed is True
        assert reclaimed is None or reclaimed.job_id != job.job_id
    finally:
        await _delete_run(session, run_id)


async def test_sweeper_reclaims_job_when_heartbeat_stops(session) -> None:
    run_id = await _create_run(session)
    await _enqueue_job(session, run_id)
    store = TeachingPackJobStore(session)
    claimed = await store.claim_next(
        "worker-a",
        lease_seconds=1,
        now=datetime(2020, 1, 1, tzinfo=UTC),
    )

    recovered = await sweep_stuck_jobs(session, max_attempts=3)
    status = await _job_status(session, claimed.job_id if claimed is not None else "missing")
    await session.commit()

    try:
        assert claimed is not None
        assert claimed.job_id in recovered
        assert status is RunJobStatus.PENDING
    finally:
        await _delete_run(session, run_id)


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-heartbeat"),
        raw_request="Teach heartbeat",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session, run_id: RunId):
    return await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-{uuid4()}",
        payload={"initial_state": {"run_id": run_id}},
    ))


async def _job_status(session, job_id: str) -> RunJobStatus:
    result = await session.execute(select(RunJob.status).where(RunJob.job_id == job_id))
    return result.scalar_one()


async def _delete_run(session, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()
