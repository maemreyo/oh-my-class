"""Backpressure checks for Teaching Pack run creation.

Enforces per-teacher and global limits on concurrent active runs to prevent
resource exhaustion.  When the active limit is hit but the queue has room,
runs are queued with an ``eligible_at`` timestamp instead of being rejected.
Must be checked *before* a new run is created.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_models import RunJob, RunJobStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


ACTIVE_STATUSES = frozenset({
    RunStatus.PENDING,
    RunStatus.PLANNING,
    RunStatus.RESEARCHING,
    RunStatus.GENERATING,
    RunStatus.REVIEWING,
    RunStatus.AWAITING_APPROVAL,
    RunStatus.EXPORTING,
})


@dataclass(frozen=True, slots=True)
class BackpressureConfig:
    """Tunable limits for backpressure enforcement."""

    max_active_runs_per_teacher: int = 3
    max_queued_runs_per_teacher: int = 5
    max_total_active_runs: int = 20
    max_total_queued_runs: int = 50
    queue_delay_seconds: int = 30


@dataclass(frozen=True, slots=True)
class BackpressureResult:
    """Outcome of a backpressure check."""

    allowed: bool
    queued: bool
    reason: str
    active_for_teacher: int
    queued_for_teacher: int
    total_active: int
    total_queued: int
    eligible_at: datetime | None = None


async def check_backpressure(
    teacher_id: str,
    db: AsyncSession,
    config: BackpressureConfig | None = None,
) -> BackpressureResult:
    """Check whether a new run may be created for *teacher_id*.

    Counts active runs (all statuses except ``completed``, ``failed``,
    ``cancelled``) per-teacher and globally, then applies the limits in
    ``config``.

    Returns a ``BackpressureResult`` with three possible outcomes:

    * ``allowed=True, queued=False`` — run starts immediately with a PENDING job.
    * ``allowed=False, queued=True`` — run is created with a QUEUED job that
      becomes claimable after ``eligible_at``.
    * ``allowed=False, queued=False`` — creation rejected (429).
    """
    cfg = config or BackpressureConfig()

    # ── per-teacher active count ──
    teacher_stmt = select(func.count()).where(
        Run.teacher_id == teacher_id,
        Run.status.in_(ACTIVE_STATUSES),
    )
    teacher_result = await db.execute(teacher_stmt)
    active_for_teacher: int = teacher_result.scalar_one()

    # ── global active count ──
    global_stmt = select(func.count()).where(
        Run.status.in_(ACTIVE_STATUSES),
    )
    global_result = await db.execute(global_stmt)
    total_active: int = global_result.scalar_one()

    # ── per-teacher queued count ──
    teacher_run_ids = select(Run.run_id).where(Run.teacher_id == teacher_id)
    queued_teacher_stmt = select(func.count()).where(
        RunJob.run_id.in_(teacher_run_ids),
        RunJob.status == RunJobStatus.QUEUED,
    )
    queued_teacher_result = await db.execute(queued_teacher_stmt)
    queued_for_teacher: int = queued_teacher_result.scalar_one()

    # ── global queued count ──
    global_queued_stmt = select(func.count()).where(
        RunJob.status == RunJobStatus.QUEUED,
    )
    global_queued_result = await db.execute(global_queued_stmt)
    total_queued: int = global_queued_result.scalar_one()

    # ── under active limits → allowed ──
    if (
        active_for_teacher < cfg.max_active_runs_per_teacher
        and total_active < cfg.max_total_active_runs
    ):
        return BackpressureResult(
            allowed=True,
            queued=False,
            reason="ok",
            active_for_teacher=active_for_teacher,
            queued_for_teacher=queued_for_teacher,
            total_active=total_active,
            total_queued=total_queued,
        )

    # ── per-teacher queue limit check ──
    if queued_for_teacher >= cfg.max_queued_runs_per_teacher:
        return BackpressureResult(
            allowed=False,
            queued=False,
            reason=(
                f"per_teacher_queue_limit:"
                f"{queued_for_teacher}/{cfg.max_queued_runs_per_teacher}"
            ),
            active_for_teacher=active_for_teacher,
            queued_for_teacher=queued_for_teacher,
            total_active=total_active,
            total_queued=total_queued,
        )

    # ── global queue limit check ──
    if total_queued >= cfg.max_total_queued_runs:
        return BackpressureResult(
            allowed=False,
            queued=False,
            reason=f"global_queue_limit:{total_queued}/{cfg.max_total_queued_runs}",
            active_for_teacher=active_for_teacher,
            queued_for_teacher=queued_for_teacher,
            total_active=total_active,
            total_queued=total_queued,
        )

    # ── queue the run ──
    now = datetime.now(UTC)
    eligible_at = now + timedelta(seconds=cfg.queue_delay_seconds)
    return BackpressureResult(
        allowed=False,
        queued=True,
        reason="queued",
        active_for_teacher=active_for_teacher,
        queued_for_teacher=queued_for_teacher,
        total_active=total_active,
        total_queued=total_queued,
        eligible_at=eligible_at,
    )
