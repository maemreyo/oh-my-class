"""Publish an approved slide_deck version into a live Teaching Session
(#458, ADR-056).

The one explicit bridge between the Creator's approval mechanism
(`ArtifactSnapshot.approved_at`) and the Teaching Session runtime
(`TeachingSession.snapshot_id`): "Live slide delivery must pin approved
content rather than creating another mutable content authority."

This mints a brand-new session pinned to the current approved version --
it is `teaching_session.service.create_session`'s first production caller
(previously exercised only by tests). It does not push updates into an
already-running session: the live sync layer
(`teaching_session/event_log.py` / `live_sync.py`) only carries
navigation/interaction events today, no slide content, so re-publishing a
newer approved version while a session is already live is a separate,
larger gap (a real content-delivery channel plus a presentation surface,
neither of which exist in this repo yet) left for a follow-up issue.

Mounted at `/teaching-packs` (not `/teaching-sessions`, which is a blanket
JWT-exempt prefix for session-token-gated routes) so `require_teacher`'s
account-JWT auth actually applies.
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.routers.teaching_pack_deps import (
    TEACHING_PACK_SESSION,
    get_run_with_ownership,
)
from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore
from services.gateway.teaching_pack_types import RunId
from services.gateway.teaching_session.models import RetentionTier
from services.gateway.teaching_session.service import create_session

router = APIRouter()


class PublishLiveSessionRequest(BaseModel):
    class_id: str | None = None
    retention_tier: RetentionTier = RetentionTier.AGGREGATE


class PublishLiveSessionResponse(BaseModel):
    session_id: str
    room_code: str | None
    snapshot_id: str


@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/run/{run_id}/artifacts/{artifact_id}/publish-live-session",
    response_model=PublishLiveSessionResponse,
)
@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/runs/{run_id}/artifacts/{artifact_id}/publish-live-session",
    response_model=PublishLiveSessionResponse,
)
async def publish_approved_slide_deck_to_live_session(
    run_id: str,
    artifact_id: str,
    payload: PublishLiveSessionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> PublishLiveSessionResponse:
    """Fail closed unless the artifact is a slide_deck with an approved head
    snapshot -- an unapproved or in-progress edit must never become a live,
    student-facing session."""
    typed_run_id = RunId(run_id)
    await get_run_with_ownership(run_id, current_user, session)

    snapshot_store = TeachingPackSnapshotStore(session)
    head = await snapshot_store.get_latest_snapshot(typed_run_id, artifact_id)
    if head is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found")
    if head.artifact_type != "slide_deck":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"error": "not_a_slide_deck", "artifact_type": head.artifact_type},
        )
    if head.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="slide_deck_not_approved",
        )

    teaching_session = await create_session(
        session,
        session_id=f"session-{uuid4()}",
        teacher_id=current_user.user_id,
        deck_id=artifact_id,
        snapshot_id=head.snapshot_id,
        class_id=payload.class_id,
        retention_tier=payload.retention_tier,
    )
    await session.commit()
    return PublishLiveSessionResponse(
        session_id=teaching_session.session_id,
        room_code=teaching_session.room_code,
        snapshot_id=teaching_session.snapshot_id,
    )
