from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobCreate
from services.gateway.teaching_pack_models import RunJobKind, RunJobStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

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
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestTeachingPackJobStore:
    async def test_enqueue_start_job_persists_pending_job(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        store = TeachingPackJobStore(session)

        job = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "create_run"},
        ))
        await session.commit()

        assert job.run_id == run_id
        assert job.kind is RunJobKind.START
        assert job.status is RunJobStatus.PENDING

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_duplicate_idempotency_key_returns_existing_job(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        store = TeachingPackJobStore(session)
        idempotency_key = f"idem-{uuid4()}"

        first = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.RESUME,
            idempotency_key=idempotency_key,
            payload={"gate_response_id": "response-1"},
        ))
        second = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.RESUME,
            idempotency_key=idempotency_key,
            payload={"gate_response_id": "response-1"},
        ))
        await session.commit()

        assert second.job_id == first.job_id
        assert second.idempotency_key == idempotency_key

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_list_pending_orders_by_creation(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        store = TeachingPackJobStore(session)
        first = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"n": 1},
        ))
        second = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.RESUME,
            idempotency_key=f"idem-{uuid4()}",
            payload={"n": 2},
        ))
        await session.commit()

        pending = await store.list_pending(limit=10)

        assert [job.job_id for job in pending if job.run_id == run_id] == [
            first.job_id,
            second.job_id,
        ]

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_enqueue_with_eligible_at_creates_queued_job(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        store = TeachingPackJobStore(session)
        eligible = datetime(2099, 1, 1, tzinfo=UTC)

        job = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "queue-test"},
            eligible_at=eligible,
        ))
        await session.commit()

        assert job.status is RunJobStatus.QUEUED
        assert job.eligible_at == eligible

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_enqueue_without_eligible_at_creates_pending_job(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        store = TeachingPackJobStore(session)

        job = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "queue-test"},
        ))
        await session.commit()

        assert job.status is RunJobStatus.PENDING
        assert job.eligible_at is None

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_idempotent_enqueue_returns_existing_queued_job(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        store = TeachingPackJobStore(session)
        idem_key = f"idem-{uuid4()}"
        eligible = datetime(2099, 1, 1, tzinfo=UTC)

        first = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=idem_key,
            payload={"source": "idem-test"},
            eligible_at=eligible,
        ))
        second = await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=idem_key,
            payload={"source": "idem-test"},
            eligible_at=eligible,
        ))
        await session.commit()

        assert second.job_id == first.job_id
        assert second.status is RunJobStatus.QUEUED
        assert second.eligible_at == eligible

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


async def _create_run(session: AsyncSession) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach jobs",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id
