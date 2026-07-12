from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus
from services.gateway.slo_metrics import compute_slo_snapshot
from services.gateway.teaching_pack_models import GateInterrupt, GateInterruptStatus, RunJob, RunJobKind, RunJobStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@dataclass(frozen=True, slots=True)
class RunSeed:
    prefix: str
    suffix: str
    teacher_id: str
    status: RunStatus
    now: datetime
    latency_seconds: int
    cost_usd: float


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, checkfirst=True))
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestSloMetrics:
    async def test_seeded_runs_produce_success_rate_latency_queue_gate_and_cost(
        self,
        session: AsyncSession,
    ) -> None:
        prefix = f"slo-{uuid4()}"
        teacher_id = f"teacher-slo-{uuid4()}"
        now = datetime(2099, 6, 30, 8, tzinfo=UTC)
        completed = _run(RunSeed(prefix, "completed", teacher_id, RunStatus.COMPLETED, now, 60, 1.25))
        failed = _run(RunSeed(prefix, "failed", teacher_id, RunStatus.FAILED, now, 180, 2.75))
        session.add_all([completed, failed])
        session.add(_job(prefix, completed.run_id, RunJobStatus.PENDING, now))
        session.add(_job(f"{prefix}-dlq", failed.run_id, RunJobStatus.DEAD_LETTER, now))
        session.add(_gate(prefix, completed.run_id, now - timedelta(minutes=5)))
        await session.commit()

        try:
            snapshot = await compute_slo_snapshot(session, now=now)

            teacher = snapshot.teachers[teacher_id]
            assert teacher.run_count == 2
            assert teacher.success_rate == 0.5
            assert teacher.run_latency_p95_seconds == 180
            assert teacher.queue_depth == 1
            assert teacher.gate_backlog == 1
            # #124: dead-letter growth is the metric the page-alert rule watches.
            assert teacher.dead_letter_count == 1
            assert teacher.cost_usd_today == 4.0
            assert snapshot.global_dimension.success_rate == 0.5
            # Global aggregates across all teachers/tests sharing this DB, so
            # assert presence rather than an exact count (matches the existing
            # queue_depth/gate_backlog tests, which only check the teacher
            # dimension for exact counts).
            assert snapshot.global_dimension.dead_letter_count >= 1
        finally:
            await session.execute(delete(Run).where(Run.run_id.in_([completed.run_id, failed.run_id])))
            await session.commit()

    async def test_unexpired_gate_is_not_backlog(self, session: AsyncSession) -> None:
        prefix = f"slo-{uuid4()}"
        teacher_id = f"teacher-gate-{uuid4()}"
        now = datetime(2099, 6, 30, 8, tzinfo=UTC)
        run = _run(RunSeed(prefix, "waiting", teacher_id, RunStatus.AWAITING_APPROVAL, now, 30, 0.0))
        session.add(run)
        session.add(_gate(prefix, run.run_id, now + timedelta(hours=1)))
        await session.commit()

        try:
            snapshot = await compute_slo_snapshot(session, now=now)
            assert snapshot.teachers[teacher_id].gate_backlog == 0
        finally:
            await session.execute(delete(Run).where(Run.run_id == run.run_id))
            await session.commit()


def _run(seed: RunSeed) -> Run:
    created_at = seed.now - timedelta(seconds=seed.latency_seconds)
    return Run(
        run_id=f"{seed.prefix}-{seed.suffix}",
        teacher_id=seed.teacher_id,
        status=seed.status,
        raw_request="SLO metric test",
        created_at=created_at,
        updated_at=seed.now,
        cost_usd=seed.cost_usd,
    )


def _job(prefix: str, run_id: str, status: RunJobStatus, now: datetime) -> RunJob:
    return RunJob(
        job_id=f"job-{prefix}",
        run_id=run_id,
        kind=RunJobKind.START,
        status=status,
        idempotency_key=f"idem-{prefix}",
        payload={"source": "slo-test"},
        created_at=now,
        updated_at=now,
    )


def _gate(prefix: str, run_id: str, expires_at: datetime) -> GateInterrupt:
    _ = prefix
    return GateInterrupt(
        gate_id=f"gate-{uuid4()}",
        run_id=run_id,
        gate_name="content_approval",
        status=GateInterruptStatus.ACTIVE,
        payload={"gate": "content_approval"},
        expires_at=expires_at,
    )
