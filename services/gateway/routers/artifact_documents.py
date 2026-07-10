"""Registry-driven V2 artifact editing, versioning, review, and approval (#431, ADR-055)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from common.contracts.artifact_document import ArtifactDocument, ArtifactPayload, DocumentAuthority
from services.gateway.artifact_approval_service import (
    ArtifactNotCurrentError,
    BlockingReviewNotesOpenError,
    approve_all_current,
    approve_artifact_version,
)
from services.gateway.artifact_document_edit_service import (
    ArtifactHasNoVersionsError,
    ArtifactVersionNotFoundError,
    EditOutcome,
    edit_artifact_document,
    restore_artifact_document,
)
from services.gateway.artifact_document_store import ArtifactDocumentStore
from services.gateway.artifact_rewrite_proposal import (
    BlockNotFoundError,
    BlockRewriteInstructionError,
    RewriteUnavailableError,
    UnsupportedPayloadForRewriteError,
    propose_block_rewrite,
)
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.review_note_store import ReviewNoteCreate, ReviewNoteRead, ReviewNoteStore
from services.gateway.routers.teaching_pack_deps import (
    TEACHING_PACK_SESSION,
    get_run_with_ownership,
    get_run_with_reviewer_access,
)
from services.gateway.run_delegation_store import RunDelegationStore
from services.gateway.slide_deck_ai_rewrite_rate_limit import (
    SlideDeckAiRewriteRateLimitState,
    allow_ai_rewrite_attempt,
)
from services.gateway.teaching_pack_snapshot_errors import StaleArtifactVersionError
from services.gateway.teaching_pack_types import RunId

router = APIRouter()


class ArtifactVersionSummaryResponse(BaseModel):
    version: int
    authority: str
    created_at: datetime


class EditArtifactDocumentRequest(BaseModel):
    base_version: int = Field(ge=1)
    payload: ArtifactPayload
    authority: DocumentAuthority = "teacher_edit"


class RestoreArtifactDocumentRequest(BaseModel):
    target_version: int = Field(ge=1)


class EditArtifactDocumentResponse(BaseModel):
    document: ArtifactDocument
    impacted_artifact_ids: list[str]


class RewriteProposalRequest(BaseModel):
    content_entity_id: str = Field(min_length=1, max_length=80)
    preset: str | None = None
    instruction: str | None = Field(default=None, max_length=2_000)


class RewriteProposalResponse(BaseModel):
    entity_id: str
    before: str
    after: str


class CreateReviewNoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2_000)
    blocking: bool = False
    content_entity_id: str | None = Field(default=None, max_length=80)


class ReviewNoteResponse(BaseModel):
    note_id: str
    artifact_id: str
    content_entity_id: str | None
    author_id: str
    body: str
    blocking: bool
    status: str


class ApproveArtifactRequest(BaseModel):
    version: int = Field(ge=1)


class ApproveAllCurrentRequest(BaseModel):
    artifact_ids: list[str] = Field(min_length=1)


class ApproveAllCurrentResponse(BaseModel):
    approved: list[str]
    blocked: list[dict[str, str]]


class DelegateReviewerRequest(BaseModel):
    delegate_id: str = Field(min_length=1, max_length=64)


class DelegateReviewerResponse(BaseModel):
    delegation_id: str
    delegate_id: str


@router.get(
    "/runs/{run_id}/artifacts/{artifact_id}/versions",
    response_model=list[ArtifactVersionSummaryResponse],
)
async def list_artifact_document_versions(
    run_id: str,
    artifact_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> list[ArtifactVersionSummaryResponse]:
    await get_run_with_reviewer_access(run_id, current_user, session)
    versions = await ArtifactDocumentStore(session).list_versions(RunId(run_id), artifact_id)
    return [
        ArtifactVersionSummaryResponse(
            version=v.version, authority=v.authority, created_at=v.created_at,
        )
        for v in versions
    ]


@router.post(
    "/runs/{run_id}/artifacts/{artifact_id}/edit",
    response_model=EditArtifactDocumentResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_artifact_document_route(
    run_id: str,
    artifact_id: str,
    payload: EditArtifactDocumentRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> EditArtifactDocumentResponse:
    await get_run_with_reviewer_access(run_id, current_user, session)
    try:
        outcome = await edit_artifact_document(
            session,
            run_id=RunId(run_id),
            artifact_id=artifact_id,
            base_version=payload.base_version,
            payload=payload.payload,
            authority=payload.authority,
        )
    except ArtifactHasNoVersionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found",
        ) from exc
    except StaleArtifactVersionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_stale_version_detail(exc),
        ) from exc
    await session.commit()
    return _edit_response(outcome)


@router.post(
    "/runs/{run_id}/artifacts/{artifact_id}/restore",
    response_model=EditArtifactDocumentResponse,
)
async def restore_artifact_document_route(
    run_id: str,
    artifact_id: str,
    payload: RestoreArtifactDocumentRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> EditArtifactDocumentResponse:
    await get_run_with_reviewer_access(run_id, current_user, session)
    try:
        outcome = await restore_artifact_document(
            session,
            run_id=RunId(run_id),
            artifact_id=artifact_id,
            target_version=payload.target_version,
        )
    except (ArtifactHasNoVersionsError, ArtifactVersionNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="artifact_version_not_found",
        ) from exc
    except StaleArtifactVersionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_stale_version_detail(exc),
        ) from exc
    await session.commit()
    return _edit_response(outcome)


@router.post(
    "/runs/{run_id}/artifacts/{artifact_id}/rewrite-proposal",
    response_model=RewriteProposalResponse,
)
async def propose_artifact_block_rewrite(
    run_id: str,
    artifact_id: str,
    payload: RewriteProposalRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    request: Request,
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> RewriteProposalResponse:
    """Ephemeral -- generates and returns a proposal, never persists it (ADR-055)."""
    await get_run_with_reviewer_access(run_id, current_user, session)
    if not allow_ai_rewrite_attempt(
        _ai_rewrite_rate_limit_state(request),
        teacher_id=current_user.user_id,
        now=datetime.now(UTC),
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="ai_rewrite_rate_limited",
        )
    latest = await ArtifactDocumentStore(session).get_latest(RunId(run_id), artifact_id)
    if latest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found")
    document = ArtifactDocument.model_validate(latest.document_json)
    try:
        proposal = await propose_block_rewrite(
            run_id=run_id,
            document=document,
            content_entity_id=payload.content_entity_id,
            preset=payload.preset,
            instruction=payload.instruction,
        )
    except UnsupportedPayloadForRewriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_payload",
        ) from exc
    except BlockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="block_not_found",
        ) from exc
    except BlockRewriteInstructionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        ) from exc
    except RewriteUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="rewrite_unavailable",
        ) from exc
    return RewriteProposalResponse(
        entity_id=proposal.entity_id, before=proposal.before, after=proposal.after,
    )


@router.post(
    "/runs/{run_id}/artifacts/{artifact_id}/notes",
    response_model=ReviewNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review_note(
    run_id: str,
    artifact_id: str,
    payload: CreateReviewNoteRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ReviewNoteResponse:
    await get_run_with_reviewer_access(run_id, current_user, session)
    latest = await ArtifactDocumentStore(session).get_latest(RunId(run_id), artifact_id)
    if latest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found")
    note = await ReviewNoteStore(session).create(ReviewNoteCreate(
        note_id=f"note-{uuid4().hex[:16]}",
        run_id=RunId(run_id),
        artifact_id=artifact_id,
        document_id=latest.document_id,
        author_id=current_user.user_id,
        body=payload.body,
        blocking=payload.blocking,
        content_entity_id=payload.content_entity_id,
    ))
    await session.commit()
    return _note_response(note)


@router.get("/runs/{run_id}/artifacts/{artifact_id}/notes", response_model=list[ReviewNoteResponse])
async def list_review_notes(
    run_id: str,
    artifact_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> list[ReviewNoteResponse]:
    await get_run_with_reviewer_access(run_id, current_user, session)
    notes = await ReviewNoteStore(session).list_for_artifact(RunId(run_id), artifact_id)
    return [_note_response(note) for note in notes]


@router.post("/runs/{run_id}/notes/{note_id}/resolve", response_model=ReviewNoteResponse)
async def resolve_review_note(
    run_id: str,
    note_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ReviewNoteResponse:
    await get_run_with_reviewer_access(run_id, current_user, session)
    note = await ReviewNoteStore(session).resolve(note_id)
    await session.commit()
    return _note_response(note)


@router.post(
    "/runs/{run_id}/artifacts/{artifact_id}/approve",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def approve_artifact(
    run_id: str,
    artifact_id: str,
    payload: ApproveArtifactRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> None:
    await get_run_with_reviewer_access(run_id, current_user, session)
    try:
        await approve_artifact_version(
            session,
            run_id=RunId(run_id),
            artifact_id=artifact_id,
            version=payload.version,
            approver_id=current_user.user_id,
        )
    except ArtifactNotCurrentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "artifact_not_current", "current_version": exc.current_version},
        ) from exc
    except BlockingReviewNotesOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="blocking_review_note_open",
        ) from exc
    await session.commit()


@router.post("/runs/{run_id}/approve-all-current", response_model=ApproveAllCurrentResponse)
async def approve_all_current_route(
    run_id: str,
    payload: ApproveAllCurrentRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ApproveAllCurrentResponse:
    await get_run_with_reviewer_access(run_id, current_user, session)
    result = await approve_all_current(
        session,
        run_id=RunId(run_id),
        artifact_ids=payload.artifact_ids,
        approver_id=current_user.user_id,
    )
    await session.commit()
    return ApproveAllCurrentResponse(approved=result.approved, blocked=result.blocked)


@router.post(
    "/runs/{run_id}/delegate",
    response_model=DelegateReviewerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def delegate_reviewer(
    run_id: str,
    payload: DelegateReviewerRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> DelegateReviewerResponse:
    """Owner-only via `get_run_with_ownership` -- delegation is not itself delegable."""
    await get_run_with_ownership(run_id, current_user, session)
    delegation = await RunDelegationStore(session).grant(
        RunId(run_id), payload.delegate_id, current_user.user_id,
    )
    await session.commit()
    return DelegateReviewerResponse(
        delegation_id=delegation.delegation_id, delegate_id=delegation.delegate_id,
    )


def _edit_response(outcome: EditOutcome) -> EditArtifactDocumentResponse:
    return EditArtifactDocumentResponse(
        document=outcome.document,
        impacted_artifact_ids=outcome.impacted_artifact_ids,
    )


def _stale_version_detail(exc: StaleArtifactVersionError) -> dict[str, object]:
    return {
        "error": "base_version_stale",
        "base_version": exc.base_version,
        "current_version": exc.current_version,
    }


def _note_response(note: ReviewNoteRead) -> ReviewNoteResponse:
    return ReviewNoteResponse(
        note_id=note.note_id,
        artifact_id=note.artifact_id,
        content_entity_id=note.content_entity_id,
        author_id=note.author_id,
        body=note.body,
        blocking=note.blocking,
        status=note.status,
    )


def _ai_rewrite_rate_limit_state(request: Request) -> SlideDeckAiRewriteRateLimitState:
    state = getattr(request.app.state, "slide_deck_ai_rewrite_rate_limit_state", None)
    if state is None:
        state = SlideDeckAiRewriteRateLimitState()
        request.app.state.slide_deck_ai_rewrite_rate_limit_state = state
    return state
