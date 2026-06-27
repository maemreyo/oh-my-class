from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.pipeline_v2_models import RunJob, RunJobKind, RunJobStatus
from services.gateway.pipeline_v2_types import JsonObject, RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class RunJobCreate:
    job_id: str
    run_id: RunId
    kind: RunJobKind
    idempotency_key: str
    payload: JsonObject
    eligible_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RunJobRead:
    job_id: str
    run_id: RunId
    kind: RunJobKind
    status: RunJobStatus
    idempotency_key: str
    payload: JsonObject
    attempts: int
    eligible_at: datetime | None = None


class PipelineV2JobStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, payload: RunJobCreate) -> RunJobRead:
        initial_status = (
            RunJobStatus.QUEUED if payload.eligible_at is not None else RunJobStatus.PENDING
        )
        statement = pg_insert(RunJob).values(
            job_id=payload.job_id,
            run_id=payload.run_id,
            kind=payload.kind,
            status=initial_status,
            idempotency_key=payload.idempotency_key,
            payload=payload.payload,
            eligible_at=payload.eligible_at,
            attempts=0,
        ).on_conflict_do_nothing(
            index_elements=["idempotency_key"],
        )
        await self._session.execute(statement)
        await self._session.flush()
        return await self.get_by_idempotency_key(payload.idempotency_key)

    async def find_by_idempotency_key(self, idempotency_key: str) -> RunJobRead | None:
        statement = select(RunJob).where(RunJob.idempotency_key == idempotency_key)
        result = await self._session.execute(statement)
        job = result.scalar_one_or_none()
        if job is None:
            return None
        return _read_job(job)

    async def get_by_idempotency_key(self, idempotency_key: str) -> RunJobRead:
        statement = select(RunJob).where(RunJob.idempotency_key == idempotency_key)
        result = await self._session.execute(statement)
        job = result.scalar_one()
        return _read_job(job)

    async def list_pending(self, limit: int) -> list[RunJobRead]:
        statement = (
            select(RunJob)
            .where(RunJob.status == RunJobStatus.PENDING)
            .order_by(RunJob.created_at)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [_read_job(job) for job in result.scalars().all()]

    async def claim_next(
        self,
        lease_owner: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> RunJobRead | None:
        claim_time = now or datetime.now(UTC)
        statement = (
            select(RunJob)
            .where(
                or_(
                    RunJob.status == RunJobStatus.PENDING,
                    and_(
                        RunJob.status == RunJobStatus.QUEUED,
                        RunJob.eligible_at.is_not(None),
                        RunJob.eligible_at <= claim_time,
                    ),
                    RunJob.status == RunJobStatus.RUNNING,
                ),
                or_(RunJob.lease_expires_at.is_(None), RunJob.lease_expires_at <= claim_time),
            )
            .order_by(RunJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        result = await self._session.execute(statement)
        job = result.scalar_one_or_none()
        if job is None:
            return None
        job.status = RunJobStatus.RUNNING
        job.lease_owner = lease_owner
        job.lease_expires_at = claim_time + timedelta(seconds=lease_seconds)
        job.attempts += 1
        await self._session.flush()
        return _read_job(job)

    async def mark_completed(self, job_id: str) -> bool:
        job = await self._get_job_for_update(job_id)
        if job.status is not RunJobStatus.RUNNING:
            return False
        job.status = RunJobStatus.COMPLETED
        job.lease_owner = None
        job.lease_expires_at = None
        await self._session.flush()
        return True

    async def mark_failed(self, job_id: str) -> bool:
        job = await self._get_job_for_update(job_id)
        if job.status is not RunJobStatus.RUNNING:
            return False
        job.status = RunJobStatus.FAILED
        job.lease_owner = None
        job.lease_expires_at = None
        await self._session.flush()
        return True

    async def cancel_run_jobs(self, run_id: RunId) -> int:
        statement = (
            select(RunJob)
            .where(
                RunJob.run_id == run_id,
                or_(
                    RunJob.status == RunJobStatus.PENDING,
                    RunJob.status == RunJobStatus.QUEUED,
                    RunJob.status == RunJobStatus.RUNNING,
                ),
            )
            .with_for_update()
        )
        result = await self._session.execute(statement)
        jobs = list(result.scalars().all())
        for job in jobs:
            job.status = RunJobStatus.CANCELLED
            job.lease_owner = None
            job.lease_expires_at = None
        await self._session.flush()
        return len(jobs)

    async def promote_eligible(
        self,
        limit: int,
        now: datetime | None = None,
    ) -> list[str]:
        """Promote QUEUED jobs whose ``eligible_at`` has passed to PENDING.

        Returns the list of promoted job IDs.
        """
        claim_time = now or datetime.now(UTC)
        statement = (
            select(RunJob)
            .where(
                RunJob.status == RunJobStatus.QUEUED,
                RunJob.eligible_at.is_not(None),
                RunJob.eligible_at <= claim_time,
            )
            .order_by(RunJob.eligible_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(statement)
        jobs = list(result.scalars().all())
        promoted_ids: list[str] = []
        for job in jobs:
            job.status = RunJobStatus.PENDING
            promoted_ids.append(job.job_id)
        if promoted_ids:
            await self._session.flush()
        return promoted_ids

    async def _get_job_for_update(self, job_id: str) -> RunJob:
        statement = select(RunJob).where(RunJob.job_id == job_id).with_for_update()
        result = await self._session.execute(statement)
        return result.scalar_one()


def _read_job(job: RunJob) -> RunJobRead:
    return RunJobRead(
        job_id=job.job_id,
        run_id=RunId(job.run_id),
        kind=job.kind,
        status=job.status,
        idempotency_key=job.idempotency_key,
        payload=job.payload,
        attempts=job.attempts,
        eligible_at=job.eligible_at,
    )
