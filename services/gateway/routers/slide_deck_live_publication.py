"""Publish an approved slide_deck version into a live Teaching Session
(#458, ADR-056).

The one explicit bridge between the Creator's approval mechanism
(`ArtifactSnapshot.approved_at`) and the Teaching Session runtime
(`TeachingSession.snapshot_id`): "Live slide delivery must pin approved
content rather than creating another mutable content authority."

This mints a brand-new session pinned to the current approved version --
it is `teaching_session.service.create_session`'s first production caller
(previously exercised only by tests).

`republish_approved_slide_deck_to_live_session` below closes the gap this
module's initial version left open: re-pinning an *already-running*
session's `snapshot_id` to a newer approved version, with a
`content_republished` session event so connected clients (via
`routers/teaching_session_live.py`'s `/stream`) know to refetch content
from that router's `GET /{session_id}/content`. This is an explicit,
teacher-initiated, audited event -- never a silent mutation -- consistent
with ADR-056's "Live delivery never mutates the canonical pack silently"
(it never touches the canonical pack either; only this session's own pin).

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
from services.gateway.teaching_session import live_sync
from services.gateway.teaching_session.event_log import record_event
from services.gateway.teaching_session.events import SessionEventType
from services.gateway.teaching_session.join import JOINABLE_STATUSES
from services.gateway.teaching_session.models import RetentionTier, TeachingSession
from services.gateway.teaching_session.service import create_session
from services.gateway.teaching_session.tokens import SessionRole

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


class RepublishLiveSessionRequest(BaseModel):
    session_id: str


class RepublishLiveSessionResponse(BaseModel):
    session_id: str
    snapshot_id: str
    republished: bool


@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/run/{run_id}/artifacts/{artifact_id}/republish-live-session",
    response_model=RepublishLiveSessionResponse,
)
@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/runs/{run_id}/artifacts/{artifact_id}/republish-live-session",
    response_model=RepublishLiveSessionResponse,
)
async def republish_approved_slide_deck_to_live_session(
    run_id: str,
    artifact_id: str,
    payload: RepublishLiveSessionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> RepublishLiveSessionResponse:
    """Re-pin an already-live session to the artifact's current approved head.

    Same fail-closed artifact checks as the initial publish, plus checks
    scoped to the *session* being mutated (never covered by
    `get_run_with_ownership`, which only checks the *run*):
    `session.deck_id` must match `artifact_id`, and `session.teacher_id`
    must be the caller -- otherwise a teacher who owns a different run that
    happens to reuse the same local `artifact_id` string could re-pin
    another teacher's live session.
    """
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

    teaching_session = await session.get(TeachingSession, payload.session_id)
    if teaching_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    if teaching_session.deck_id != artifact_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="session_deck_mismatch",
        )
    if teaching_session.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="session_not_owned_by_teacher",
        )
    if teaching_session.status not in JOINABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="session_not_joinable",
        )

    if teaching_session.snapshot_id == head.snapshot_id:
        return RepublishLiveSessionResponse(
            session_id=teaching_session.session_id,
            snapshot_id=teaching_session.snapshot_id,
            republished=False,
        )

    teaching_session.snapshot_id = head.snapshot_id
    recorded = await record_event(
        session,
        session_id=teaching_session.session_id,
        event_type=SessionEventType.CONTENT_REPUBLISHED,
        actor_role=SessionRole.CONTROLLER,
        payload={"snapshot_id": head.snapshot_id},
    )
    await session.commit()
    if not recorded.duplicate:
        await live_sync.set_hot_state(recorded.read_model)
        await live_sync.publish_event(recorded.event)
    return RepublishLiveSessionResponse(
        session_id=teaching_session.session_id,
        snapshot_id=teaching_session.snapshot_id,
        republished=True,
    )
