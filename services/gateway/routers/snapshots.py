"""Snapshot creation endpoints — produce and retrieve artifact snapshots."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from services.gateway.artifact_snapshot_service import produce_artifact_snapshot
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.exceptions import AuthorizationError, NotFoundError
from services.gateway.pipeline_v2_types import RunId

router = APIRouter()


def _require_owner(run_data: dict[str, Any], user: User) -> None:
    if user.role == Role.ADMIN:
        return
    if run_data.get("teacher_id") != user.user_id:
        raise AuthorizationError(message="You do not have access to this run")


class ProduceSnapshotRequest(BaseModel):
    """Request to produce and persist an artifact snapshot."""

    artifact_content: dict[str, Any] = Field(
        ...,
        description="Artifact content (title, sections, theme, etc.)",
    )
    artifact_id: str | None = Field(
        None,
        description="Optional artifact ID; generated if not provided",
    )
    artifact_type: str = Field(
        "lesson",
        description="Type of artifact (lesson, worksheet, quiz, etc.)",
    )
    renderer_version: str = Field(
        "1.0",
        description="Version of the renderer used",
    )
    template_version: str = Field(
        "unknown",
        description="Version of the template used",
    )
    theme_version: str = Field(
        "unknown",
        description="Version of the theme used",
    )


class ProduceSnapshotResponse(BaseModel):
    """Response containing the created snapshot ID."""

    snapshot_id: str


@router.post("/{run_id}/snapshots")  # pyright: ignore[reportUntypedFunctionDecorator]
async def produce_snapshot(
    run_id: str,
    request_body: ProduceSnapshotRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ProduceSnapshotResponse:
    """Produce and persist an artifact snapshot.

    Takes artifact content, renders it to standalone HTML, strips student answer keys,
    and persists the snapshot to the database.

    This is a production caller for the artifact_snapshot_service.produce_artifact_snapshot()
    function, demonstrating the complete renderer → snapshot flow in action.
    """
    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    _require_owner(run_data, current_user)

    # Get database session from app state
    async with http_request.app.state.pipeline_v2_session_factory() as session:
        snapshot_id = await produce_artifact_snapshot(
            session,
            run_id=RunId(run_id),
            artifact_content=request_body.artifact_content,
            artifact_id=request_body.artifact_id,
            artifact_type=request_body.artifact_type,
            renderer_version=request_body.renderer_version,
            template_version=request_body.template_version,
            theme_version=request_body.theme_version,
        )
        await session.commit()

    return ProduceSnapshotResponse(snapshot_id=snapshot_id)
