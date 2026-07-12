from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.auth.dependencies import require_admin
from services.gateway.auth.models import User
from services.gateway.slo_metrics import SloSnapshot, compute_slo_snapshot
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_job_store import TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJob, TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/slo")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_slo_snapshot(
    _current_user: Annotated[User, Depends(require_admin)],
    session: AsyncSession = Depends(get_teaching_pack_session),
) -> SloSnapshot:
    return await compute_slo_snapshot(session)


class DeadLetterJobResponse(BaseModel):
    job_id: str
    run_id: str
    kind: str
    idempotency_key: str
    attempts: int
    error_classification: str | None
    last_error: str | None
    dead_lettered_at: str | None


class DeadLetterJobListResponse(BaseModel):
    jobs: list[DeadLetterJobResponse]


class ReplayDeadLetterJobResponse(BaseModel):
    job_id: str
    replayed: bool


@router.get("/dead-letter-jobs")  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_dead_letter_jobs(
    _current_user: Annotated[User, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    session: AsyncSession = Depends(get_teaching_pack_session),
) -> DeadLetterJobListResponse:
    """#124: ops-admin inspection view for poison (dead-lettered) jobs."""
    jobs = await TeachingPackJobStore(session).list_dead_letter(limit=limit)
    return DeadLetterJobListResponse(jobs=[
        DeadLetterJobResponse(
            job_id=job.job_id,
            run_id=str(job.run_id),
            kind=job.kind.value,
            idempotency_key=job.idempotency_key,
            attempts=job.attempts,
            error_classification=job.error_classification,
            last_error=job.last_error,
            dead_lettered_at=job.dead_lettered_at.isoformat() if job.dead_lettered_at else None,
        )
        for job in jobs
    ])


@router.post("/dead-letter-jobs/{job_id}/replay")  # pyright: ignore[reportUntypedFunctionDecorator]
async def replay_dead_letter_job(
    job_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    session: AsyncSession = Depends(get_teaching_pack_session),
) -> ReplayDeadLetterJobResponse:
    """#124: ops-triggered replay -- resets a dead-lettered job to `pending`
    with a clean attempt count so it can be re-claimed. system_admin only,
    same as inspection; never a teacher affordance. Emits an ADMIN-visibility
    audit event (who/when) on the affected run for traceability."""
    try:
        replayed = await TeachingPackJobStore(session).replay_dead_letter(job_id)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dead_letter_job_not_found") from exc
    if not replayed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dead_letter_job_not_found")

    run_id_row = await session.execute(select(RunJob.run_id).where(RunJob.job_id == job_id))
    run_id = run_id_row.scalar_one()
    await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
        run_id=RunId(run_id),
        event_name="admin.dead_letter.replayed",
        visibility=TeachingPackEventVisibility.ADMIN,
        payload={
            "admin_id": current_user.user_id,
            "job_id": job_id,
            "replayed_at": datetime.now(UTC).isoformat(),
        },
    ))
    await session.commit()
    return ReplayDeadLetterJobResponse(job_id=job_id, replayed=True)
