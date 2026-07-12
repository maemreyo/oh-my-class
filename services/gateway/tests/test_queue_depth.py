from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.queue_depth import count_claimable_run_jobs
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
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
        await session.execute(delete(Run).where(Run.run_id.like("test-queue-depth-%")))
        await session.commit()
    yield factory
    async with factory() as session:
        await session.execute(delete(Run).where(Run.run_id.like("test-queue-depth-%")))
        await session.commit()
    await engine.dispose()


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-queue-depth-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-queue-depth"),
        raw_request="Teach queue depth",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue(session, run_id: RunId, *, eligible_at: datetime | None = None) -> None:
    await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-{uuid4()}",
        payload={"initial_state": {"run_id": run_id}},
        eligible_at=eligible_at,
    ))


async def test_counts_pending_and_eligible_queued_only(session_factory) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        run_id = await _create_run(session)
        await _enqueue(session, run_id)  # PENDING -- claimable
        await _enqueue(session, run_id, eligible_at=now - timedelta(seconds=1))  # QUEUED, due -- claimable
        await _enqueue(session, run_id, eligible_at=now + timedelta(hours=1))  # QUEUED, not due yet
        await session.commit()

        depth = await count_claimable_run_jobs(session, now=now)

    assert depth == 2
