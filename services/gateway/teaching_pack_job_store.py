from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.teaching_pack_models import RunJob, RunJobKind, RunJobStatus
from services.gateway.teaching_pack_types import JsonObject, RunId

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
    last_error: str | None = None
    error_classification: str | None = None
    dead_lettered_at: datetime | None = None


class TeachingPackJobStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

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

    async def mark_dead_letter(
        self,
        job_id: str,
        *,
        error_summary: str,
        classification: str,
        now: datetime | None = None,
    ) -> bool:
        """#124: move a RUNNING job to DEAD_LETTER -- a holding state, not a
        terminal one. Excluded from every claimable query the same as FAILED
        (neither PENDING, eligible-QUEUED, nor RUNNING), but inspectable and
        replayable by ops instead of a dead end.
        """
        job = await self._get_job_for_update(job_id)
        if job.status is not RunJobStatus.RUNNING:
            return False
        job.status = RunJobStatus.DEAD_LETTER
        job.lease_owner = None
        job.lease_expires_at = None
        job.last_error = error_summary[:2000]
        job.error_classification = classification
        job.dead_lettered_at = now or datetime.now(UTC)
        await self._session.flush()
        return True

    async def replay_dead_letter(self, job_id: str) -> bool:
        """#124: ops-triggered re-enqueue of a dead-lettered job.

        Resets to PENDING with a clean attempt count -- replay rides on the
        same idempotency-key/exactly-once-effects machinery as any other
        (re-)claim, so a replayed run does not duplicate side effects.
        """
        job = await self._get_job_for_update(job_id)
        if job.status is not RunJobStatus.DEAD_LETTER:
            return False
        job.status = RunJobStatus.PENDING
        job.attempts = 0
        job.eligible_at = None
        job.last_error = None
        job.error_classification = None
        job.dead_lettered_at = None
        await self._session.flush()
        return True

    async def requeue_with_backoff(
        self,
        job_id: str,
        eligible_at: datetime,
        reason: str = "provider_exhausted",
    ) -> bool:
        """Move a RUNNING job back to QUEUED with an eligible_at delay.

        Returns True if the job was updated, False if not found or not RUNNING.
        """
        job = await self._get_job_for_update(job_id)
        if job.status is not RunJobStatus.RUNNING:
            return False
        job.status = RunJobStatus.QUEUED
        job.eligible_at = eligible_at
        job.lease_owner = None
        job.lease_expires_at = None
        await self._session.flush()
        return True

    async def refresh_lease(
        self,
        job_id: str,
        lease_owner: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        claim_time = now or datetime.now(UTC)
        statement = (
            select(RunJob)
            .where(
                RunJob.job_id == job_id,
                RunJob.status == RunJobStatus.RUNNING,
                RunJob.lease_owner == lease_owner,
            )
            .with_for_update()
        )
        result = await self._session.execute(statement)
        job = result.scalar_one_or_none()
        if job is None:
            return False
        job.lease_expires_at = claim_time + timedelta(seconds=lease_seconds)
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
        last_error=job.last_error,
        error_classification=job.error_classification,
        dead_lettered_at=job.dead_lettered_at,
    )
