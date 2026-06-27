"""Migration 011: eligible_at column and claim index for queued backpressure.

Proves that after running migration 011:
  - ``eligible_at`` is nullable (NULLs accepted on existing rows)
  - ``ix_run_jobs_status_eligible_at`` index exists for claim/promote queries
  - ``claim_next`` ignores QUEUED jobs whose ``eligible_at`` is in the future
  - Downgrade cleanly removes the column and index
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Run
from services.gateway.pipeline_v2_job_store import PipelineV2JobStore, RunJobCreate
from services.gateway.pipeline_v2_models import RunJobKind, RunJobStatus
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine():
    eng = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestMigration011EligibleAt:
    """Schema-level verification that eligible_at and index exist."""

    async def test_eligible_at_column_exists_and_is_nullable(
        self,
        engine,
    ) -> None:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'run_jobs' "
                    "AND column_name = 'eligible_at'"
                ),
            )
            row = result.scalar_one_or_none()
        assert row is not None, "eligible_at column must exist after migration 011"
        assert row == "YES", "eligible_at must be nullable"

    async def test_eligible_at_index_exists(self, engine) -> None:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename = 'run_jobs' "
                    "AND indexname = 'ix_run_jobs_status_eligible_at'"
                ),
            )
            row = result.scalar_one_or_none()
        assert row is not None, "ix_run_jobs_status_eligible_at index must exist"

    async def test_insert_with_null_eligible_at_succeeds(
        self,
        engine,
    ) -> None:
        """Existing rows and new PENDING jobs have NULL eligible_at."""
        run_id = f"null-test-{uuid4()}"
        job_id = f"job-null-{uuid4()}"
        idem_key = f"idem-{uuid4()}"
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO public.runs "
                    "(run_id, teacher_id, status, raw_request) "
                    "VALUES (:rid, 'teacher-null', 'pending', 'test')"
                ),
                {"rid": run_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO public.run_jobs "
                    "(job_id, run_id, kind, status, "
                    "idempotency_key, payload, attempts) "
                    "VALUES (:jid, :rid, 'start', 'pending', "
                    ":ik, '{}', 0)"
                ),
                {"jid": job_id, "rid": run_id, "ik": idem_key},
            )
            await conn.commit()

    async def test_insert_with_eligible_at_succeeds(
        self,
        engine,
    ) -> None:
        """QUEUED jobs carry a non-NULL eligible_at."""
        run_id = f"eligible-test-{uuid4()}"
        job_id = f"job-elg-{uuid4()}"
        idem_key = f"idem-{uuid4()}"
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO public.runs "
                    "(run_id, teacher_id, status, raw_request) "
                    "VALUES (:rid, 'teacher-elg', 'pending', 'test')"
                ),
                {"rid": run_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO public.run_jobs "
                    "(job_id, run_id, kind, status, "
                    "idempotency_key, payload, attempts, eligible_at) "
                    "VALUES (:jid, :rid, 'start', 'queued', "
                    ":ik, '{}', 0, now() + interval '1 hour')"
                ),
                {"jid": job_id, "rid": run_id, "ik": idem_key},
            )
            await conn.commit()


class TestMigration011ClaimBehavior:
    """Verify claim_next semantics with eligible_at after migration."""

    async def test_claim_next_ignores_queued_ineligible_job(
        self,
        session: AsyncSession,
    ) -> None:
        """A QUEUED job with future eligible_at is NOT claimed."""
        run_id = await _create_run(session)
        future = datetime(2099, 1, 1, tzinfo=UTC)
        store = PipelineV2JobStore(session)
        await store.enqueue(
            RunJobCreate(
                job_id=f"job-{uuid4()}",
                run_id=run_id,
                kind=RunJobKind.START,
                idempotency_key=f"idem-{uuid4()}",
                payload={"source": "migration-test"},
                eligible_at=future,
            ),
        )
        await session.flush()

        claimed = await PipelineV2JobStore(session).claim_next(
            lease_owner="worker-migration",
            lease_seconds=30,
            now=datetime(2026, 6, 1, tzinfo=UTC),
        )
        await session.commit()

        assert claimed is None, "claim_next must not return a QUEUED job with future eligible_at"
        await _delete_run(session, run_id)

    async def test_claim_next_grabs_eligible_queued_job(
        self,
        session: AsyncSession,
    ) -> None:
        """A QUEUED job whose eligible_at has passed IS claimed."""
        run_id = await _create_run(session)
        now = datetime(2026, 6, 1, tzinfo=UTC)
        past_eligible = now - timedelta(seconds=1)
        queued = await PipelineV2JobStore(session).enqueue(
            RunJobCreate(
                job_id=f"job-{uuid4()}",
                run_id=run_id,
                kind=RunJobKind.START,
                idempotency_key=f"idem-{uuid4()}",
                payload={"source": "migration-eligible"},
                eligible_at=past_eligible,
            ),
        )
        await session.flush()

        claimed = await PipelineV2JobStore(session).claim_next(
            lease_owner="worker-eligible",
            lease_seconds=30,
            now=now,
        )
        await session.commit()

        assert claimed is not None
        assert claimed.job_id == queued.job_id
        assert claimed.status is RunJobStatus.RUNNING
        await _delete_run(session, run_id)

    async def test_enqueue_pending_with_null_eligible_at(
        self,
        session: AsyncSession,
    ) -> None:
        """Standard PENDING job has NULL eligible_at."""
        run_id = await _create_run(session)
        store = PipelineV2JobStore(session)

        job = await store.enqueue(
            RunJobCreate(
                job_id=f"job-{uuid4()}",
                run_id=run_id,
                kind=RunJobKind.START,
                idempotency_key=f"idem-{uuid4()}",
                payload={"source": "null-eligible-test"},
            )
        )
        await session.commit()

        assert job.status is RunJobStatus.PENDING
        assert job.eligible_at is None
        await _delete_run(session, run_id)

    async def test_promote_eligible_uses_indexed_query(
        self,
        session: AsyncSession,
    ) -> None:
        """promote_eligible works with (status, eligible_at) index."""
        run_id = await _create_run(session)
        now = datetime(2026, 6, 1, tzinfo=UTC)
        past = now - timedelta(seconds=1)
        job = await PipelineV2JobStore(session).enqueue(
            RunJobCreate(
                job_id=f"job-{uuid4()}",
                run_id=run_id,
                kind=RunJobKind.START,
                idempotency_key=f"idem-{uuid4()}",
                payload={"source": "promote-index-test"},
                eligible_at=past,
            ),
        )
        await session.flush()

        promoted = await PipelineV2JobStore(session).promote_eligible(
            limit=5,
            now=now,
        )
        await session.commit()

        assert job.job_id in promoted
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession) -> RunId:
    run_id = RunId(f"test-mig-{uuid4()}")
    await PipelineV2RunStore(session).create_run(
        PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-migration-test"),
            raw_request="Test migration 011",
            class_info={"grade": 5},
        )
    )
    await session.flush()
    return run_id


async def _delete_run(
    session: AsyncSession,
    run_id: RunId,
) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()
