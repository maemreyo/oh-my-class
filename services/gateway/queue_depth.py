"""Global claimable `run_jobs` count -- the autoscaling signal for #119 (OPS-06).

Distinct from `slo_metrics._queue_depth_by_teacher`: that counts *all*
PENDING/QUEUED jobs per teacher (dashboard view). This counts only jobs a
worker could actually claim *right now* -- PENDING, or QUEUED with
`eligible_at` already due -- matching `claim_next`'s first two branches
(`teaching_pack_job_store.py`). That's the number the autoscaler must act on:
a QUEUED-but-not-yet-eligible (backoff-delayed) job isn't backlog pressure.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.teaching_pack_models import RunJob, RunJobStatus


async def count_claimable_run_jobs(session: AsyncSession, *, now: datetime | None = None) -> int:
    claim_time = now or datetime.now(UTC)
    statement = select(func.count(RunJob.job_id)).where(
        or_(
            RunJob.status == RunJobStatus.PENDING,
            and_(
                RunJob.status == RunJobStatus.QUEUED,
                RunJob.eligible_at.is_not(None),
                RunJob.eligible_at <= claim_time,
            ),
        ),
    )
    result = await session.execute(statement)
    return int(result.scalar_one())
