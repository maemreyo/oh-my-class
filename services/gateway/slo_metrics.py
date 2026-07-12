from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_models import GateInterrupt, GateInterruptStatus, RunJob, RunJobStatus


@dataclass(frozen=True, slots=True)
class SloDimension:
    name: str
    teacher_id: str | None
    run_count: int
    success_rate: float | None
    run_latency_p95_seconds: float | None
    stage_latency_p95_seconds: dict[str, float]
    gate_backlog: int
    queue_depth: int
    cost_usd_today: float
    # #124: defaulted so existing call sites building an SloDimension without
    # this metric don't need updating.
    dead_letter_count: int = 0


@dataclass(frozen=True, slots=True)
class SloSnapshot:
    generated_at: datetime
    window_started_at: datetime
    global_dimension: SloDimension
    teachers: dict[str, SloDimension] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SloDimensionInput:
    name: str
    teacher_id: str | None
    runs: list[Run]
    queue_depth: int
    gate_backlog: int
    dead_letter_count: int
    cost_usd_today: float


async def compute_slo_snapshot(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    window: timedelta = timedelta(hours=24),
) -> SloSnapshot:
    generated_at = now or datetime.now(UTC)
    window_started_at = generated_at - window
    runs = list((await session.execute(
        select(Run).where(Run.created_at >= window_started_at, Run.deleted_at.is_(None)),
    )).scalars())
    queue_rows = await _queue_depth_by_teacher(session)
    gate_rows = await _gate_backlog_by_teacher(session, generated_at)
    dead_letter_rows = await _dead_letter_count_by_teacher(session)
    cost_rows = await _cost_today_by_teacher(session, generated_at)
    teacher_ids = {run.teacher_id for run in runs}
    teacher_ids |= set(queue_rows) | set(gate_rows) | set(dead_letter_rows) | set(cost_rows)
    teachers = sorted(teacher_ids)
    teacher_dimensions = {
        teacher_id: _dimension(
            SloDimensionInput(
                name=f"teacher:{teacher_id}",
                teacher_id=teacher_id,
                runs=[run for run in runs if run.teacher_id == teacher_id],
                queue_depth=queue_rows.get(teacher_id, 0),
                gate_backlog=gate_rows.get(teacher_id, 0),
                dead_letter_count=dead_letter_rows.get(teacher_id, 0),
                cost_usd_today=cost_rows.get(teacher_id, 0.0),
            ),
        )
        for teacher_id in teachers
    }
    return SloSnapshot(
        generated_at=generated_at,
        window_started_at=window_started_at,
        global_dimension=_dimension(
            SloDimensionInput(
                name="global",
                teacher_id=None,
                runs=runs,
                queue_depth=sum(queue_rows.values()),
                gate_backlog=sum(gate_rows.values()),
                dead_letter_count=sum(dead_letter_rows.values()),
                cost_usd_today=sum(cost_rows.values()),
            ),
        ),
        teachers=teacher_dimensions,
    )


def _dimension(data: SloDimensionInput) -> SloDimension:
    terminal_runs = [run for run in data.runs if run.status in _TERMINAL_STATUSES]
    completed = sum(1 for run in terminal_runs if run.status is RunStatus.COMPLETED)
    latencies = [
        (run.updated_at - run.created_at).total_seconds()
        for run in terminal_runs
        if run.updated_at is not None and run.created_at is not None
    ]
    return SloDimension(
        name=data.name,
        teacher_id=data.teacher_id,
        run_count=len(data.runs),
        success_rate=None if not terminal_runs else completed / len(terminal_runs),
        run_latency_p95_seconds=_p95(latencies),
        stage_latency_p95_seconds={},
        gate_backlog=data.gate_backlog,
        queue_depth=data.queue_depth,
        dead_letter_count=data.dead_letter_count,
        cost_usd_today=data.cost_usd_today,
    )


async def _dead_letter_count_by_teacher(session: AsyncSession) -> dict[str, int]:
    """#124: current dead-letter backlog per teacher -- the metric the
    page-alert rule watches for DLQ growth (ADR-034 decision 2)."""
    rows = await session.execute(
        select(Run.teacher_id, func.count(RunJob.job_id))
        .join(Run, Run.run_id == RunJob.run_id)
        .where(RunJob.status == RunJobStatus.DEAD_LETTER)
        .group_by(Run.teacher_id),
    )
    return {teacher_id: count for teacher_id, count in rows}


async def _queue_depth_by_teacher(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Run.teacher_id, func.count(RunJob.job_id))
        .join(Run, Run.run_id == RunJob.run_id)
        .where(RunJob.status.in_([RunJobStatus.PENDING, RunJobStatus.QUEUED]))
        .group_by(Run.teacher_id),
    )
    return {teacher_id: count for teacher_id, count in rows}


async def _gate_backlog_by_teacher(session: AsyncSession, now: datetime) -> dict[str, int]:
    rows = await session.execute(
        select(Run.teacher_id, func.count(GateInterrupt.gate_id))
        .join(Run, Run.run_id == GateInterrupt.run_id)
        .where(
            GateInterrupt.status == GateInterruptStatus.ACTIVE,
            GateInterrupt.expires_at.is_not(None),
            GateInterrupt.expires_at <= now,
        )
        .group_by(Run.teacher_id),
    )
    return {teacher_id: count for teacher_id, count in rows}


async def _cost_today_by_teacher(session: AsyncSession, now: datetime) -> dict[str, float]:
    today = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await session.execute(
        select(Run.teacher_id, func.coalesce(func.sum(Run.cost_usd), 0.0))
        .where(Run.created_at >= today, Run.deleted_at.is_(None))
        .group_by(Run.teacher_id),
    )
    return {teacher_id: float(cost) for teacher_id, cost in rows}


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(round((len(ordered) * 0.95) + 0.5) - 1, 0)
    return ordered[min(index, len(ordered) - 1)]


_TERMINAL_STATUSES: Final = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})
