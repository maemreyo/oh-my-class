"""Notification and admin recovery routes.

Teacher endpoints:
  GET  /notifications           — list notifications for authenticated teacher
  POST /notifications/{id}/read — mark a notification as read
  POST /notifications/{id}/dismiss — dismiss a delivery on a channel

Admin endpoints:
  GET  /admin/runs/{run_id}/summary — safe run summary (no PII)
  POST /admin/runs/{run_id}/recover — execute a recovery action
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from ..admin_recovery import (
    AdminRecoveryRequest,
    SafeRecoveryAction,
    execute_recovery,
)
from ..auth.dependencies import require_admin, require_teacher
from ..auth.models import User  # noqa: TC001
from ..exceptions import NotFoundError
from ..models import Run, RunStatus
from ..notification_store import (
    dismiss_notification,
    get_notifications,
    mark_read,
)
from ..pipeline_v2_db import get_pipeline_v2_session
from ..pipeline_v2_store import PipelineV2RunStore
from ..pipeline_v2_types import RunId

router = APIRouter()
PIPELINE_V2_SESSION = Depends(get_pipeline_v2_session)


# ── Schemas ────────────────────────────────────────────────────────


class NotificationResponse(BaseModel):
    notification_id: str
    run_id: str
    teacher_id: str
    event_type: str
    title: str
    message: str
    metadata: dict[str, Any]
    created_at: Any
    read_at: Any | None = None


class DismissRequest(BaseModel):
    channel: str = "in_app"


class RunSummaryResponse(BaseModel):
    run_id: str
    teacher_id: str
    status: str
    raw_request_summary: str
    current_step: int


class AdminRunListItem(BaseModel):
    run_id: str
    teacher_id: str
    status: str
    raw_request_summary: str
    current_step: int


class AdminRunListResponse(BaseModel):
    runs: list[AdminRunListItem]
    limit: int
    offset: int


class RecoveryRequest(BaseModel):
    action: SafeRecoveryAction
    reason: str


class RecoveryResponse(BaseModel):
    success: bool
    message: str
    action_performed: str


# ── Teacher endpoints ──────────────────────────────────────────────


@router.get("", response_model=list[NotificationResponse])  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_notifications(
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
    unread_only: bool = False,
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> list[NotificationResponse]:
    """List notifications for the authenticated teacher."""
    notifications = await get_notifications(
        current_user.user_id, session, unread_only=unread_only,
    )
    return [NotificationResponse(**n) for n in notifications]


@router.post("/{notification_id}/read", response_model=dict[str, str])  # pyright: ignore[reportUntypedFunctionDecorator]
async def read_notification(
    notification_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> dict[str, str]:
    """Mark a notification as read."""
    # Verify ownership
    notifications = await get_notifications(current_user.user_id, session)
    owned_ids = {n["notification_id"] for n in notifications}
    if notification_id not in owned_ids:
        raise NotFoundError(message="Notification not found")
    await mark_read(notification_id, session)
    await session.commit()
    return {"status": "ok"}


@router.post("/{notification_id}/dismiss", response_model=dict[str, str])  # pyright: ignore[reportUntypedFunctionDecorator]
async def dismiss(
    notification_id: str,
    body: DismissRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> dict[str, str]:
    """Dismiss a notification delivery for a channel."""
    # Verify ownership
    notifications = await get_notifications(current_user.user_id, session)
    owned_ids = {n["notification_id"] for n in notifications}
    if notification_id not in owned_ids:
        raise NotFoundError(message="Notification not found")
    await dismiss_notification(notification_id, body.channel, session)
    await session.commit()
    return {"status": "dismissed"}


# ── Admin endpoints ────────────────────────────────────────────────


@router.get(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/admin/runs",
    response_model=AdminRunListResponse,
)
async def list_admin_runs(
    http_request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    status_filter: list[RunStatus] | None = None,
    teacher_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> AdminRunListResponse:
    bounded_limit = min(max(limit, 1), 100)
    bounded_offset = max(offset, 0)
    statement = (
        select(Run)
        .order_by(Run.created_at.desc())
        .limit(bounded_limit)
        .offset(bounded_offset)
    )
    if status_filter:
        statement = statement.where(Run.status.in_(status_filter))
    if teacher_id is not None:
        statement = statement.where(Run.teacher_id == teacher_id)
    result = await session.execute(statement)
    return AdminRunListResponse(
        runs=[
            AdminRunListItem(
                run_id=run.run_id,
                teacher_id=run.teacher_id,
                status=run.status.value,
                raw_request_summary=run.raw_request[:200],
                current_step=run.current_step,
            )
            for run in result.scalars().all()
        ],
        limit=bounded_limit,
        offset=bounded_offset,
    )


@router.get(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/admin/runs/{run_id}/summary",
    response_model=RunSummaryResponse,
)
async def get_run_summary(
    run_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> RunSummaryResponse:
    """Safe run summary for admin — no PII beyond teacher_id."""
    store = PipelineV2RunStore(session)
    run = await store.get_run_by_id(RunId(run_id))
    if run is None:
        raise NotFoundError(message=f"Run {run_id} not found")
    return RunSummaryResponse(
        run_id=run.run_id,
        teacher_id=run.teacher_id,
        status=run.status.value,
        raw_request_summary=run.raw_request[:200],
        current_step=1,
    )


@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/admin/runs/{run_id}/recover",
    response_model=RecoveryResponse,
)
async def recover_run(
    run_id: str,
    body: RecoveryRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> RecoveryResponse:
    """Execute a safe admin recovery action on a run."""
    # Validate run exists
    store = PipelineV2RunStore(session)
    run = await store.get_run_by_id(RunId(run_id))
    if run is None:
        raise NotFoundError(message=f"Run {run_id} not found")

    request = AdminRecoveryRequest(
        run_id=run_id,
        action=body.action,
        reason=body.reason,
        admin_id=current_user.user_id,
    )
    result = await execute_recovery(request, session)
    await session.commit()
    return RecoveryResponse(
        success=result.success,
        message=result.message,
        action_performed=result.action_performed,
    )
