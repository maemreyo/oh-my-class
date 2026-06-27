"""Stuck job and gate escalation recovery sweeper.

Periodically run by a background task to reclaim stuck jobs and escalate
long-open gate interrupts.  Replaces the spec's ``worker_id`` / ``heartbeat``
model with the actual ``lease_owner`` / ``lease_expires_at`` columns on
``RunJob``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_models import (
    GateInterrupt,
    GateInterruptStatus,
    RunJob,
    RunJobStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Default maximum number of times a job may be retried before permanent failure.
DEFAULT_MAX_ATTEMPTS: int = 3
# Default gate timeout — matches the 24-hour gate timeout in AGENTS.md §7.
DEFAULT_GATE_TIMEOUT_HOURS: int = 24


async def sweep_stuck_jobs(
    db: AsyncSession,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> list[str]:
    """Find running jobs whose lease has expired and recover or fail them.

    For each stuck job:

    * If ``attempts < max_attempts``: reset to ``pending``, increment
      ``attempts``, clear ``lease_owner`` — the sweeper will re-claim it.
    * If ``attempts >= max_attempts``: set to ``failed``.

    Returns the list of recovered/failed job IDs.
    """
    now = datetime.now(UTC)

    statement = (
        select(RunJob)
        .where(
            RunJob.status == RunJobStatus.RUNNING,
            RunJob.lease_expires_at < now,
        )
        .order_by(RunJob.created_at)
    )
    result = await db.execute(statement)
    stuck_jobs = list(result.scalars().all())

    recovered_ids: list[str] = []
    for job in stuck_jobs:
        if job.attempts < max_attempts:
            job.status = RunJobStatus.PENDING
            job.attempts += 1
            job.lease_owner = None
            job.lease_expires_at = None
        else:
            job.status = RunJobStatus.FAILED
            job.lease_owner = None
            job.lease_expires_at = None
        recovered_ids.append(job.job_id)

    if recovered_ids:
        await db.flush()

    return recovered_ids


async def sweep_escalated_gates(
    db: AsyncSession,
    *,
    timeout_hours: int = DEFAULT_GATE_TIMEOUT_HOURS,
) -> list[str]:
    """Find gate interrupts open longer than *timeout_hours* and escalate them.

    Sets ``status`` to ``EXPIRED`` for gates that exceed the timeout.
    Returns the list of escalated gate IDs.

    Note: the DB column is ``created_at`` (not ``opened_at`` as in the spec).
    """
    cutoff = datetime.now(UTC) - timedelta(hours=timeout_hours)

    statement = (
        select(GateInterrupt)
        .where(
            GateInterrupt.status == GateInterruptStatus.ACTIVE,
            GateInterrupt.created_at < cutoff,
        )
        .order_by(GateInterrupt.created_at)
    )
    result = await db.execute(statement)
    stale_gates = list(result.scalars().all())

    escalated_ids: list[str] = []
    for gate in stale_gates:
        gate.status = GateInterruptStatus.EXPIRED
        escalated_ids.append(gate.gate_id)

    if escalated_ids:
        await db.flush()

    return escalated_ids
