from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User  # noqa: TC001
from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
from services.gateway.pipeline_v2_models import PipelineV2EventVisibility
from services.gateway.pipeline_v2_snapshot_store import (
    ArtifactSnapshotRead,
    NonStandaloneSnapshotApprovalError,
    PipelineV2SnapshotStore,
)
from services.gateway.pipeline_v2_store import PipelineV2EventCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import JsonObject, JsonValue, RunId, TeacherId
from services.gateway.routers.pipeline_v2_preview_schemas import (
    RenderedSnapshotMetadataResponse,
    SnapshotApprovalRequest,
    SnapshotApprovalResponse,
)

router = APIRouter()
PIPELINE_V2_SESSION = Depends(get_pipeline_v2_session)
PREVIEW_SECURITY_HEADERS = {
    "X-Frame-Options": "SAMEORIGIN",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:",
}


@router.get(
    "/run/{run_id}/snapshots/{snapshot_id}",
    response_model=RenderedSnapshotMetadataResponse,
)
async def get_rendered_snapshot_metadata(
    run_id: str,
    snapshot_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> RenderedSnapshotMetadataResponse:
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot = await PipelineV2SnapshotStore(session).get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    return _metadata_response(snapshot)


@router.get("/run/{run_id}/snapshots/{snapshot_id}/preview")
async def preview_rendered_snapshot(
    run_id: str,
    snapshot_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    view: Annotated[
        Literal["student", "teacher"],
        Query(),
    ] = "student",
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> HTMLResponse:
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot = await PipelineV2SnapshotStore(session).get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    if view == "teacher" and current_user.role not in (Role.TEACHER, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="teacher_preview_required",
        )
    html = snapshot.rendered_html if view == "teacher" else snapshot.student_rendered_html
    return HTMLResponse(content=html, headers=PREVIEW_SECURITY_HEADERS)


@router.post(
    "/run/{run_id}/approved-snapshots",
    response_model=SnapshotApprovalResponse,
)
async def approve_rendered_snapshots(
    run_id: str,
    payload: SnapshotApprovalRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> SnapshotApprovalResponse:
    typed_run_id = RunId(run_id)
    run_status = await _require_run_access(session, typed_run_id, current_user)
    if run_status is not RunStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run_not_awaiting_approval",
        )
    snapshot_ids = list(dict.fromkeys(payload.snapshot_ids))
    snapshot_store = PipelineV2SnapshotStore(session)
    try:
        approved_count = await snapshot_store.approve_snapshots(typed_run_id, snapshot_ids)
    except NonStandaloneSnapshotApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="non_standalone_snapshot",
        ) from exc
    if approved_count != len(snapshot_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    event_snapshot_ids: list[JsonValue] = list(snapshot_ids)
    event_payload: JsonObject = {"snapshot_ids": event_snapshot_ids}
    await PipelineV2RunStore(session).write_event(PipelineV2EventCreate(
        run_id=typed_run_id,
        event_name="pipeline_v2.content.approved_snapshots",
        visibility=PipelineV2EventVisibility.TEACHER,
        payload=event_payload,
    ))
    await session.commit()
    return SnapshotApprovalResponse(run_id=run_id, approved_snapshot_ids=snapshot_ids)


async def _require_run_access(session: AsyncSession, run_id: RunId, user: User) -> RunStatus:
    if user.role is Role.ADMIN:
        run = await PipelineV2RunStore(session).get_run_by_id(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")
        return run.status
    run = await PipelineV2RunStore(session).get_run(run_id, TeacherId(user.user_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")
    return run.status


def _metadata_response(snapshot: ArtifactSnapshotRead) -> RenderedSnapshotMetadataResponse:
    return RenderedSnapshotMetadataResponse(
        snapshot_id=snapshot.snapshot_id,
        artifact_id=snapshot.artifact_id,
        artifact_type=snapshot.artifact_type,
        content_hash=snapshot.content_hash,
        html_hash=snapshot.html_hash,
        renderer_version=snapshot.renderer_version,
        template_version=snapshot.template_version,
        theme_version=snapshot.theme_version,
        standalone_valid=snapshot.standalone_valid,
        approved_at=snapshot.approved_at,
    )
