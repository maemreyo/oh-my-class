"""Tests for operations-hardening modules: leases, sweeper, budget, backpressure.

Covers:
  - worker_lease: acquire / renew / release
  - recovery_sweeper: stuck jobs + gate escalation
  - budget: check / record / exceeded
  - backpressure: per-teacher and global limits
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.backpressure import (
    BackpressureConfig,
    check_backpressure,
)
from services.gateway.budget import (
    BudgetConfig,
    BudgetExceededError,
    BudgetLedger,
    check_budget,
    record_retry,
    record_usage,
)
from services.gateway.models import Base, Run, RunStatus
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobCreate, RunJobRead
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    RunJob,
    RunJobKind,
    RunJobStatus,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.recovery_sweeper import (
    sweep_escalated_gates,
    sweep_stuck_jobs,
)
from services.gateway.worker_lease import acquire_lease, release_lease, renew_lease

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


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

async def _create_run(session: AsyncSession, teacher_id: str = "teacher-a") -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId(teacher_id),
        raw_request="Test hardening",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session: AsyncSession, run_id: RunId) -> RunJobRead:
    job_store = TeachingPackJobStore(session)
    return await job_store.enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-{uuid4()}",
        payload={"source": "test"},
    ))


async def _claim_job(session: AsyncSession, run_id: RunId) -> RunJobRead:
    await _enqueue_job(session, run_id)
    claimed = await TeachingPackJobStore(session).claim_next(
        lease_owner="worker-a",
        lease_seconds=30,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert claimed is not None
    return claimed


async def _cleanup_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
    await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def _delete_test_runs(session: AsyncSession) -> None:
    await session.execute(delete(Run).where(Run.run_id.like("test-%")))
    await session.execute(delete(Run).where(Run.run_id.like("test-mig-%")))
    await session.execute(delete(Run).where(Run.run_id.like("null-test-%")))
    await session.execute(delete(Run).where(Run.run_id.like("eligible-test-%")))


# ===========================================================================
# Worker Lease Tests
# ===========================================================================


class TestWorkerLease:
    async def test_acquire_lease_success(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        job = await _enqueue_job(session, run_id)

        acquired = await acquire_lease(run_id, "worker-a", session, lease_seconds=30)

        assert acquired is True
        stmt = select(RunJob).where(RunJob.job_id == job.job_id)
        row = (await session.execute(stmt)).scalar_one()
        assert row.lease_owner == "worker-a"
        assert row.lease_expires_at is not None
        assert row.status is RunJobStatus.RUNNING
        assert row.attempts == 1
        await _cleanup_run(session, run_id)

    async def test_acquire_lease_conflict(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        await _enqueue_job(session, run_id)

        claim_time = datetime.now(UTC) + timedelta(minutes=10)
        store = TeachingPackJobStore(session)
        claimed = await store.claim_next(
            lease_owner="worker-a",
            lease_seconds=600,
            now=claim_time,
        )
        assert claimed is not None
        await session.flush()

        acquired = await acquire_lease(
            run_id, "worker-b", session, lease_seconds=30,
        )

        assert acquired is False
        await _cleanup_run(session, run_id)

    async def test_acquire_lease_after_expiry(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        await _claim_job(session, run_id)  # worker-a claims with 30s lease

        # Simulate lease expiry — claim with a time that makes the existing lease expired
        acquired = await acquire_lease(
            run_id, "worker-b", session, lease_seconds=30,
        )

        # Since claim_next was called with now=2026-01-01 and lease_seconds=30,
        # the lease expires at 2026-01-01 00:00:30. acquire_lease uses datetime.now(UTC)
        # which is way past that, so the lease IS expired and worker-b should succeed
        assert acquired is True
        stmt = select(RunJob).where(RunJob.run_id == run_id)
        row = (await session.execute(stmt)).scalar_one()
        assert row.lease_owner == "worker-b"
        await _cleanup_run(session, run_id)

    async def test_renew_lease_success(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        await _claim_job(session, run_id)

        renewed = await renew_lease(run_id, "worker-a", session, lease_seconds=60)

        assert renewed is True
        stmt = select(RunJob).where(RunJob.run_id == run_id)
        row = (await session.execute(stmt)).scalar_one()
        assert row.lease_owner == "worker-a"
        assert row.lease_expires_at is not None
        await _cleanup_run(session, run_id)

    async def test_renew_lease_wrong_worker(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        await _claim_job(session, run_id)

        renewed = await renew_lease(run_id, "worker-b", session, lease_seconds=60)

        assert renewed is False
        await _cleanup_run(session, run_id)

    async def test_release_lease(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        await _claim_job(session, run_id)

        await release_lease(run_id, "worker-a", session)

        stmt = select(RunJob).where(RunJob.run_id == run_id)
        row = (await session.execute(stmt)).scalar_one()
        assert row.lease_owner is None
        assert row.lease_expires_at is None
        await _cleanup_run(session, run_id)

    async def test_release_lease_idempotent(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        await _claim_job(session, run_id)
        await release_lease(run_id, "worker-a", session)

        # Second release is a no-op
        await release_lease(run_id, "worker-a", session)

        stmt = select(RunJob).where(RunJob.run_id == run_id)
        row = (await session.execute(stmt)).scalar_one()
        assert row.lease_owner is None
        await _cleanup_run(session, run_id)


# ===========================================================================
# Recovery Sweeper Tests
# ===========================================================================


class TestRecoverySweeper:
    async def test_sweep_stuck_jobs_recovery(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        job = await _claim_job(session, run_id)

        # Manually set lease to expired
        stmt = select(RunJob).where(RunJob.job_id == job.job_id)
        row = (await session.execute(stmt)).scalar_one()
        row.lease_expires_at = datetime(2020, 1, 1, tzinfo=UTC)
        await session.flush()

        recovered = await sweep_stuck_jobs(session, max_attempts=3)

        assert job.job_id in recovered
        refreshed = (await session.execute(
            select(RunJob).where(RunJob.job_id == job.job_id),
        )).scalar_one()
        assert refreshed.status is RunJobStatus.PENDING
        assert refreshed.lease_owner is None
        assert refreshed.lease_expires_at is None
        assert refreshed.attempts == 2  # incremented by claim_next earlier
        await _cleanup_run(session, run_id)

    async def test_sweep_stuck_jobs_max_attempts_dead_letters(
        self, session: AsyncSession,
    ) -> None:
        """#124: exhausting max_attempts via repeated lease expiry dead-letters
        the job (inspectable/replayable), not FAILED (terminal)."""
        run_id = await _create_run(session)
        job = await _claim_job(session, run_id)

        # Manually set attempts to max and lease to expired
        stmt = select(RunJob).where(RunJob.job_id == job.job_id)
        row = (await session.execute(stmt)).scalar_one()
        row.attempts = 3
        row.lease_expires_at = datetime(2020, 1, 1, tzinfo=UTC)
        await session.flush()

        recovered = await sweep_stuck_jobs(session, max_attempts=3)

        assert job.job_id in recovered
        refreshed = (await session.execute(
            select(RunJob).where(RunJob.job_id == job.job_id),
        )).scalar_one()
        assert refreshed.status is RunJobStatus.DEAD_LETTER
        assert refreshed.lease_owner is None
        assert refreshed.error_classification == "transient_exhausted"
        await _cleanup_run(session, run_id)

    async def test_sweep_stuck_jobs_skips_non_expired(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        await _claim_job(session, run_id)

        # Lease is not expired (expires far in future)
        stmt = select(RunJob).where(RunJob.run_id == run_id)
        row = (await session.execute(stmt)).scalar_one()
        row.lease_expires_at = datetime(2099, 1, 1, tzinfo=UTC)
        await session.flush()

        recovered = await sweep_stuck_jobs(session)

        assert len(recovered) == 0
        await _cleanup_run(session, run_id)

    async def test_sweep_escalated_gates(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        gate_id = f"gate-{uuid4()}"
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"gate_id": gate_id},
        ))
        await session.flush()

        # Manually age the gate to beyond timeout
        stmt = select(GateInterrupt).where(GateInterrupt.gate_id == gate_id)
        row = (await session.execute(stmt)).scalar_one()
        row.created_at = datetime(2020, 1, 1, tzinfo=UTC)
        await session.flush()

        escalated = await sweep_escalated_gates(session, timeout_hours=24)

        assert gate_id in escalated
        refreshed = (await session.execute(
            select(GateInterrupt).where(GateInterrupt.gate_id == gate_id),
        )).scalar_one()
        assert refreshed.status is GateInterruptStatus.EXPIRED
        await _cleanup_run(session, run_id)

    async def test_sweep_escalated_gates_skips_recent(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        gate_id = f"gate-{uuid4()}"
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"gate_id": gate_id},
        ))
        await session.flush()

        escalated = await sweep_escalated_gates(session, timeout_hours=24)

        assert gate_id not in escalated
        await _cleanup_run(session, run_id)


# ===========================================================================
# Budget Tests (pure unit — no DB)
# ===========================================================================


class TestBudget:
    def test_check_under_limit(self) -> None:
        ledger = BudgetLedger()
        config = BudgetConfig(max_tokens_per_run=1000)
        assert check_budget(ledger, config, "tokens") is True

    def test_check_at_limit(self) -> None:
        ledger = BudgetLedger(tokens_used=1000)
        config = BudgetConfig(max_tokens_per_run=1000)
        assert check_budget(ledger, config, "tokens") is False

    def test_check_over_limit(self) -> None:
        ledger = BudgetLedger(tokens_used=1500)
        config = BudgetConfig(max_tokens_per_run=1000)
        assert check_budget(ledger, config, "tokens") is False

    def test_check_searches_under_limit(self) -> None:
        ledger = BudgetLedger()
        config = BudgetConfig(max_searches_per_run=5)
        assert check_budget(ledger, config, "searches") is True

    def test_check_searches_over_limit(self) -> None:
        ledger = BudgetLedger(searches_used=5)
        config = BudgetConfig(max_searches_per_run=5)
        assert check_budget(ledger, config, "searches") is False

    def test_check_fetches_under_limit(self) -> None:
        ledger = BudgetLedger()
        config = BudgetConfig(max_fetches_per_run=10)
        assert check_budget(ledger, config, "fetches") is True

    def test_check_fetches_over_limit(self) -> None:
        ledger = BudgetLedger(fetches_used=10)
        config = BudgetConfig(max_fetches_per_run=10)
        assert check_budget(ledger, config, "fetches") is False

    def test_check_retries_under_limit(self) -> None:
        ledger = BudgetLedger(retries_used={"artifact-1": 1})
        config = BudgetConfig(max_retries_per_artifact=3)
        assert check_budget(ledger, config, "retries") is True

    def test_check_retries_over_limit(self) -> None:
        ledger = BudgetLedger(retries_used={"artifact-1": 3})
        config = BudgetConfig(max_retries_per_artifact=3)
        assert check_budget(ledger, config, "retries") is False

    def test_check_retries_empty_always_passes(self) -> None:
        ledger = BudgetLedger()
        config = BudgetConfig(max_retries_per_artifact=3)
        assert check_budget(ledger, config, "retries") is True

    def test_record_usage_tokens(self) -> None:
        ledger = BudgetLedger()
        record_usage(ledger, "tokens", amount=100)
        assert ledger.tokens_used == 100

    def test_record_usage_searches(self) -> None:
        ledger = BudgetLedger()
        record_usage(ledger, "searches", amount=3)
        assert ledger.searches_used == 3

    def test_record_usage_fetches(self) -> None:
        ledger = BudgetLedger()
        record_usage(ledger, "fetches", amount=7)
        assert ledger.fetches_used == 7

    def test_record_usage_cumulative(self) -> None:
        ledger = BudgetLedger()
        record_usage(ledger, "tokens", amount=100)
        record_usage(ledger, "tokens", amount=200)
        assert ledger.tokens_used == 300

    def test_record_retry(self) -> None:
        ledger = BudgetLedger()
        record_retry(ledger, "artifact-1")
        record_retry(ledger, "artifact-1")
        assert ledger.retries_used["artifact-1"] == 2
        assert "artifact-2" not in ledger.retries_used

    def test_record_retry_per_artifact(self) -> None:
        ledger = BudgetLedger()
        record_retry(ledger, "artifact-1")
        record_retry(ledger, "artifact-2")
        assert ledger.retries_used["artifact-1"] == 1
        assert ledger.retries_used["artifact-2"] == 1

    def test_budget_exceeded_error(self) -> None:
        err = BudgetExceededError("tokens", 1000, 500)
        assert err.budget_type == "tokens"
        assert err.current == 1000
        assert err.limit == 500
        assert "tokens" in str(err)

    def test_check_unknown_type_returns_false(self) -> None:
        ledger = BudgetLedger()
        config = BudgetConfig()
        assert check_budget(ledger, config, "unknown_type") is False

    def test_parallel_artifacts_always_passes(self) -> None:
        ledger = BudgetLedger()
        config = BudgetConfig()
        assert check_budget(ledger, config, "parallel_artifacts") is True


# ===========================================================================
# Backpressure Tests
# ===========================================================================


class TestBackpressure:
    # All backpressure tests use a very high global limit to isolate from
    # existing data in the shared test database.

    async def test_allowed_when_no_active_runs(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        result = await check_backpressure(
            teacher_id, session,
            config=BackpressureConfig(max_total_active_runs=10_000),
        )

        assert result.allowed is True
        assert result.reason == "ok"
        assert result.active_for_teacher == 0

    async def test_allowed_under_teacher_limit(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(2):
            await _create_run(session, teacher_id)

        result = await check_backpressure(
            teacher_id,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_total_active_runs=10_000,
            ),
        )

        assert result.allowed is True
        assert result.active_for_teacher == 2
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_rejected_at_teacher_limit(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(3):
            await _create_run(session, teacher_id)

        result = await check_backpressure(
            teacher_id,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=0,
                max_total_active_runs=10_000,
            ),
        )

        assert result.allowed is False
        assert result.queued is False
        assert "per_teacher_queue_limit" in result.reason
        assert result.active_for_teacher == 3
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_rejected_at_global_limit(self, session: AsyncSession) -> None:
        teacher_a = f"teacher-a-{uuid4()}"
        teacher_b = f"teacher-b-{uuid4()}"

        baseline = await check_backpressure(
            teacher_b, session,
            config=BackpressureConfig(max_total_active_runs=999_999),
        )
        baseline_total = baseline.total_active

        for _ in range(10):
            await _create_run(session, teacher_a)
        for _ in range(9):
            await _create_run(session, teacher_b)

        limit = baseline_total + 20
        mid = await check_backpressure(
            teacher_b,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=100,
                max_total_active_runs=limit,
            ),
        )
        assert mid.allowed is True

        for _ in range(11):
            await _create_run(session, teacher_b)

        result = await check_backpressure(
            teacher_b,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=100,
                max_queued_runs_per_teacher=0,
                max_total_active_runs=limit,
            ),
        )
        assert result.allowed is False
        assert result.queued is False
        assert "per_teacher_queue_limit" in result.reason

        await _cleanup_runs_for_teacher(session, teacher_a)
        await _cleanup_runs_for_teacher(session, teacher_b)

    async def test_per_teacher_isolation(self, session: AsyncSession) -> None:
        teacher_a = f"teacher-a-{uuid4()}"
        teacher_b = f"teacher-b-{uuid4()}"
        for _ in range(3):
            await _create_run(session, teacher_a)

        # teacher-b has zero runs despite teacher-a being full
        result_b = await check_backpressure(
            teacher_b,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_total_active_runs=10_000,
            ),
        )
        assert result_b.allowed is True
        assert result_b.active_for_teacher == 0

        result_a = await check_backpressure(
            teacher_a,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_total_active_runs=10_000,
            ),
        )
        assert result_a.allowed is False
        assert result_a.active_for_teacher == 3

        await _cleanup_runs_for_teacher(session, teacher_a)
        await _cleanup_runs_for_teacher(session, teacher_b)

    async def test_completed_runs_not_counted(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(3):
            run_id = await _create_run(session, teacher_id)
            stmt = select(Run).where(Run.run_id == run_id)
            row = (await session.execute(stmt)).scalar_one()
            row.status = RunStatus.COMPLETED
        await session.flush()

        result = await check_backpressure(
            teacher_id,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_total_active_runs=10_000,
            ),
        )
        assert result.allowed is True
        assert result.active_for_teacher == 0
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_failed_runs_not_counted(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(3):
            run_id = await _create_run(session, teacher_id)
            stmt = select(Run).where(Run.run_id == run_id)
            row = (await session.execute(stmt)).scalar_one()
            row.status = RunStatus.FAILED
        await session.flush()

        result = await check_backpressure(
            teacher_id,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_total_active_runs=10_000,
            ),
        )
        assert result.allowed is True
        assert result.active_for_teacher == 0
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_cancelled_runs_not_counted(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(3):
            run_id = await _create_run(session, teacher_id)
            stmt = select(Run).where(Run.run_id == run_id)
            row = (await session.execute(stmt)).scalar_one()
            row.status = RunStatus.CANCELLED
        await session.flush()

        result = await check_backpressure(
            teacher_id,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_total_active_runs=10_000,
            ),
        )
        assert result.allowed is True
        assert result.active_for_teacher == 0
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_awaiting_approval_counts_as_active(
        self, session: AsyncSession,
    ) -> None:
        teacher_id = f"teacher-{uuid4()}"
        run_id = await _create_run(session, teacher_id)
        stmt = select(Run).where(Run.run_id == run_id)
        row = (await session.execute(stmt)).scalar_one()
        row.status = RunStatus.AWAITING_APPROVAL
        await session.flush()

        result = await check_backpressure(
            teacher_id,
            session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=1,
                max_total_active_runs=10_000,
            ),
        )
        assert result.allowed is False
        assert result.active_for_teacher == 1
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_under_limit_allows_immediate_start(
        self, session: AsyncSession,
    ) -> None:
        teacher_id = f"teacher-{uuid4()}"
        result = await check_backpressure(
            teacher_id, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=5,
                max_total_active_runs=10_000,
            ),
        )

        assert result.allowed is True
        assert result.queued is False
        assert result.eligible_at is None

    async def test_active_limit_queues_when_queue_has_room(
        self, session: AsyncSession,
    ) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(3):
            await _create_run(session, teacher_id)

        result = await check_backpressure(
            teacher_id, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=5,
                max_total_active_runs=10_000,
                queue_delay_seconds=30,
            ),
        )

        assert result.allowed is False
        assert result.queued is True
        assert result.eligible_at is not None
        assert result.queued_for_teacher == 0
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_queue_limit_rejects_when_queue_full(
        self, session: AsyncSession,
    ) -> None:
        teacher_id = f"teacher-{uuid4()}"
        for _ in range(3):
            await _create_run(session, teacher_id)

        for _ in range(2):
            await _enqueue_queued_job(session, teacher_id)

        result = await check_backpressure(
            teacher_id, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=2,
                max_total_active_runs=10_000,
            ),
        )

        assert result.allowed is False
        assert result.queued is False
        assert "per_teacher_queue_limit" in result.reason
        await _cleanup_runs_for_teacher(session, teacher_id)

    async def test_global_limit_queues_when_under_global_queue_limit(
        self, session: AsyncSession,
    ) -> None:
        teacher_a = f"teacher-a-{uuid4()}"
        teacher_b = f"teacher-b-{uuid4()}"

        for _ in range(15):
            await _create_run(session, teacher_a)
        for _ in range(6):
            await _create_run(session, teacher_b)

        result = await check_backpressure(
            teacher_b, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=5,
                max_total_active_runs=20,
                max_total_queued_runs=50,
            ),
        )

        assert result.allowed is False
        assert result.queued is True
        assert result.eligible_at is not None
        assert "global" not in result.reason
        await _cleanup_runs_for_teacher(session, teacher_a)
        await _cleanup_runs_for_teacher(session, teacher_b)

    async def test_global_queue_limit_rejects_when_global_queue_full(
        self, session: AsyncSession,
    ) -> None:
        teacher_a = f"teacher-a-{uuid4()}"
        teacher_b = f"teacher-b-{uuid4()}"

        for _ in range(15):
            await _create_run(session, teacher_a)
        for _ in range(6):
            await _create_run(session, teacher_b)

        for _ in range(2):
            await _enqueue_queued_job(session, teacher_b)

        result = await check_backpressure(
            teacher_b, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=5,
                max_total_active_runs=20,
                max_total_queued_runs=2,
            ),
        )

        assert result.allowed is False
        assert result.queued is False
        assert "global_queue_limit" in result.reason
        await _cleanup_runs_for_teacher(session, teacher_a)
        await _cleanup_runs_for_teacher(session, teacher_b)

    async def test_per_teacher_queue_isolation(
        self, session: AsyncSession,
    ) -> None:
        teacher_a = f"teacher-a-{uuid4()}"
        teacher_b = f"teacher-b-{uuid4()}"

        for _ in range(3):
            await _create_run(session, teacher_a)
        for _ in range(2):
            await _enqueue_queued_job(session, teacher_a)

        result_b = await check_backpressure(
            teacher_b, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=3,
                max_total_active_runs=10_000,
                max_total_queued_runs=10_000,
            ),
        )
        assert result_b.allowed is True
        assert result_b.queued is False
        assert result_b.queued_for_teacher == 0

        result_a = await check_backpressure(
            teacher_a, session,
            config=BackpressureConfig(
                max_active_runs_per_teacher=3,
                max_queued_runs_per_teacher=3,
                max_total_active_runs=10_000,
                max_total_queued_runs=10_000,
            ),
        )
        assert result_a.allowed is False
        assert result_a.queued is True
        assert result_a.queued_for_teacher == 2

        await _cleanup_runs_for_teacher(session, teacher_a)
        await _cleanup_runs_for_teacher(session, teacher_b)


async def _enqueue_queued_job(
    session: AsyncSession,
    teacher_id: str,
) -> None:
    run_id = await _create_run(session, teacher_id)
    await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-{uuid4()}",
        payload={"source": "backpressure-test"},
        eligible_at=datetime(2099, 1, 1, tzinfo=UTC),
    ))
    await session.flush()


async def _cleanup_runs_for_teacher(
    session: AsyncSession,
    teacher_id: str,
) -> None:
    run_ids = (await session.execute(
        select(Run.run_id).where(Run.teacher_id == teacher_id),
    )).scalars().all()
    for rid in run_ids:
        await session.execute(delete(RunJob).where(RunJob.run_id == rid))
    await session.execute(delete(Run).where(Run.teacher_id == teacher_id))
    await session.commit()
