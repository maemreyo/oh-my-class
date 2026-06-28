"""Worker lease management for Teaching Pack jobs.

Provides acquire/renew/release semantics over the ``run_jobs`` table.
Lease coordination uses ``lease_owner`` and ``lease_expires_at`` columns
on the ``RunJob`` model — no external queue infrastructure required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import update

from services.gateway.teaching_pack_models import RunJob, RunJobStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def acquire_lease(
    run_id: str,
    worker_id: str,
    db: AsyncSession,
    *,
    lease_seconds: int = 300,
) -> bool:
    """Try to claim an exclusive lease on a pending or expired-running job.

    Succeeds when the job exists, is in ``pending`` status, and either has no
    current lease-owner or the lease has expired.  Uses a single UPDATE
    statement so the operation is atomic at the DB level.

    Returns ``True`` if the lease was acquired, ``False`` otherwise.
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=lease_seconds)
    statement = (
        update(RunJob)
        .where(
            RunJob.run_id == run_id,
            RunJob.status.in_([RunJobStatus.PENDING, RunJobStatus.RUNNING]),
            (RunJob.lease_owner.is_(None)) | (RunJob.lease_expires_at < now),
        )
        .values(
            lease_owner=worker_id,
            lease_expires_at=expires_at,
            attempts=RunJob.attempts + 1,
            status=RunJobStatus.RUNNING,
        )
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(statement)
    await db.flush()
    return result.rowcount > 0


async def renew_lease(
    run_id: str,
    worker_id: str,
    db: AsyncSession,
    *,
    lease_seconds: int = 300,
) -> bool:
    """Extend the lease for a job currently held by *worker_id*.

    Returns ``True`` if the lease was renewed, ``False`` if the job does
    not exist, is not owned by *worker_id*, or is not in ``running`` status.
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=lease_seconds)
    statement = (
        update(RunJob)
        .where(
            RunJob.run_id == run_id,
            RunJob.lease_owner == worker_id,
            RunJob.status == RunJobStatus.RUNNING,
        )
        .values(lease_expires_at=expires_at)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(statement)
    await db.flush()
    return result.rowcount > 0


async def release_lease(
    run_id: str,
    worker_id: str,
    db: AsyncSession,
) -> None:
    """Release the lease on a job held by *worker_id*.

    Clears ``lease_owner`` and ``lease_expires_at``.  Idempotent — no-ops
    if the job is not owned by *worker_id*.
    """
    statement = (
        update(RunJob)
        .where(
            RunJob.run_id == run_id,
            RunJob.lease_owner == worker_id,
        )
        .values(lease_owner=None, lease_expires_at=None)
        .execution_options(synchronize_session=False)
    )
    await db.execute(statement)
    await db.flush()
