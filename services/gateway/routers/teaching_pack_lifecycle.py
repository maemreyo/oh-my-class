"""Cancel, delete, and restore endpoints for pipeline V2 runs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_control_store import TeachingPackControlStore
from services.gateway.teaching_pack_job_store import TeachingPackJobStore
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import (
    InvalidRunStatusTransitionError,
    TeachingPackEventCreate,
    TeachingPackEventRead,
    TeachingPackRunStore,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import RunId
from services.gateway.routers.teaching_pack_deps import (
    TEACHING_PACK_SESSION,
    get_deleted_run_with_ownership,
    get_run_with_ownership,
)
from services.gateway.routers.teaching_pack_schemas import (
    TeachingPackCancelResponse,
    TeachingPackDeleteResponse,
    TeachingPackRestoreResponse,
    TeachingPackRunStatusResponse,
)
from services.gateway.soft_delete import restore_run, soft_delete_run

lifecycle_router = APIRouter()


@lifecycle_router.get("/run/{run_id}", response_model=TeachingPackRunStatusResponse)
@lifecycle_router.get("/runs/{run_id}", response_model=TeachingPackRunStatusResponse)
async def get_teaching_pack_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingPackRunStatusResponse:
    run = await get_run_with_ownership(run_id, current_user, session)
    events = await TeachingPackRunStore(session).replay_events(RunId(run_id))
    return TeachingPackRunStatusResponse(
        run_id=run.run_id,
        status=run.status,
        raw_request=run.raw_request,
        artifact_statuses=_latest_artifact_statuses(events),
    )


def _latest_artifact_statuses(events: list[TeachingPackEventRead]) -> list[dict[str, object]]:
    for event in reversed(events):
        payload = event.payload or {}
        values = payload.get("artifact_statuses")
        if isinstance(values, list):
            return [dict(value) for value in values if isinstance(value, dict)]
    return []


@lifecycle_router.post("/run/{run_id}/cancel", response_model=TeachingPackCancelResponse)
@lifecycle_router.post("/runs/{run_id}/cancel", response_model=TeachingPackCancelResponse)
async def cancel_teaching_pack_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingPackCancelResponse:
    await get_run_with_ownership(run_id, current_user, session)
    typed_run_id = RunId(run_id)
    run_store = TeachingPackRunStore(session)

    cancelled_jobs = await TeachingPackJobStore(session).cancel_run_jobs(typed_run_id)
    cancelled_gates = await TeachingPackControlStore(session).cancel_active_gates(typed_run_id)
    try:
        await run_store.transition_status(TeachingPackStatusTransition(
            run_id=typed_run_id,
            status=RunStatus.CANCELLED,
            stage=None,
            reason="teacher_cancelled",
        ))
    except InvalidRunStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cancel_not_allowed",
        ) from exc
    await run_store.write_event(TeachingPackEventCreate(
        run_id=typed_run_id,
        event_name="teaching_pack.run.cancelled",
        visibility=TeachingPackEventVisibility.TEACHER,
        payload={
            "actor_id": current_user.user_id,
            "reason": "teacher_cancelled",
            "cancelled_jobs": cancelled_jobs,
            "cancelled_gates": cancelled_gates,
        },
    ))
    await session.commit()
    return TeachingPackCancelResponse(
        run_id=run_id,
        status=RunStatus.CANCELLED,
        cancelled_jobs=cancelled_jobs,
    )


@lifecycle_router.delete(
    "/run/{run_id}",
    response_model=TeachingPackDeleteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@lifecycle_router.delete(
    "/runs/{run_id}",
    response_model=TeachingPackDeleteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_teaching_pack_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingPackDeleteResponse:
    """Soft-delete a run.  The run is hidden from normal queries but
    retained for the configured retention period before hard purge."""
    await get_run_with_ownership(run_id, current_user, session)
    await soft_delete_run(run_id, current_user.user_id, session)
    await session.commit()
    return TeachingPackDeleteResponse(run_id=run_id, deleted=True)


@lifecycle_router.post(
    "/run/{run_id}/restore",
    response_model=TeachingPackRestoreResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@lifecycle_router.post(
    "/runs/{run_id}/restore",
    response_model=TeachingPackRestoreResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def restore_teaching_pack_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingPackRestoreResponse:
    """Restore a soft-deleted run, making it visible again."""
    await get_deleted_run_with_ownership(run_id, current_user, session)
    await restore_run(run_id, current_user.user_id, session)
    await session.commit()
    return TeachingPackRestoreResponse(run_id=run_id, restored=True)
