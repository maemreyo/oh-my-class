"""Content Brief creation, append-only strategy review, and compliance verification (#433)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from common.contracts.content_brief import AnswerPolicy, ContentBrief, MethodologySource
from common.contracts.run_contract import ArtifactType  # noqa: TC001
from common.contracts.strategy_review import (
    FillFailureReason,
    SpecialistComplianceError,
    SpecialistOutputDeclaration,
    StrategyChangeKind,
    StrategyChangeRequest,
    TypedFillFailure,
    enforce_content_brief_compliance,
)
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.content_brief_store import (
    ContentBriefStore,
    StrategyReviewStore,
)
from services.gateway.routers.teaching_pack_deps import (
    TEACHING_PACK_SESSION,
    get_run_with_reviewer_access,
)

router = APIRouter()


class CreateContentBriefRequest(BaseModel):
    artifact_type: ArtifactType
    objectives: list[str] = Field(min_length=1)
    scope: list[str] = Field(default_factory=list)
    methodology: str = Field(min_length=1, max_length=80)
    methodology_source: MethodologySource
    learning_moves: list[str] = Field(default_factory=list)
    eligible_component_variants: list[str] = Field(default_factory=list)
    terminology: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    answer_policy: AnswerPolicy = "none"
    dependency_document_ids: list[str] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)


class FillFailureRequest(BaseModel):
    reason: FillFailureReason
    detail: str = Field(min_length=1, max_length=2_000)


class StrategyChangeRequestBody(BaseModel):
    change_kind: StrategyChangeKind
    rationale: str = Field(min_length=1, max_length=2_000)


class StrategyReviewEntryResponse(BaseModel):
    request_id: str
    request_type: str
    reason_or_kind: str
    detail: str
    status: str
    created_at: datetime


@router.post(
    "/runs/{run_id}/content-briefs",
    response_model=ContentBrief,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_brief(
    run_id: str,
    payload: CreateContentBriefRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ContentBrief:
    await get_run_with_reviewer_access(run_id, current_user, session)
    brief = ContentBrief(
        content_brief_id=f"brief-{uuid4().hex[:16]}",
        run_id=run_id,
        **payload.model_dump(),
    )
    await ContentBriefStore(session).create(brief)
    await session.commit()
    return brief


@router.get("/runs/{run_id}/content-briefs/{content_brief_id}", response_model=ContentBrief)
async def get_content_brief(
    run_id: str,
    content_brief_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ContentBrief:
    await get_run_with_reviewer_access(run_id, current_user, session)
    brief = await ContentBriefStore(session).get(content_brief_id)
    if brief is None or brief.run_id != run_id:
        raise _content_brief_not_found()
    return brief


@router.post(
    "/runs/{run_id}/content-briefs/{content_brief_id}/fill-failures",
    status_code=status.HTTP_201_CREATED,
)
async def record_fill_failure(
    run_id: str,
    content_brief_id: str,
    payload: FillFailureRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> dict[str, str]:
    await get_run_with_reviewer_access(run_id, current_user, session)
    await _require_brief_in_run(session, run_id, content_brief_id)
    request_id = await StrategyReviewStore(session).record_fill_failure(TypedFillFailure(
        content_brief_id=content_brief_id, reason=payload.reason, detail=payload.detail,
    ))
    await session.commit()
    return {"request_id": request_id}


@router.post(
    "/runs/{run_id}/content-briefs/{content_brief_id}/strategy-change-requests",
    status_code=status.HTTP_201_CREATED,
)
async def record_strategy_change_request(
    run_id: str,
    content_brief_id: str,
    payload: StrategyChangeRequestBody,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> dict[str, str]:
    await get_run_with_reviewer_access(run_id, current_user, session)
    await _require_brief_in_run(session, run_id, content_brief_id)
    request = StrategyChangeRequest(
        content_brief_id=content_brief_id,
        change_kind=payload.change_kind,
        rationale=payload.rationale,
    )
    request_id = await StrategyReviewStore(session).record_strategy_change_request(request)
    await session.commit()
    return {"request_id": request_id}


@router.get(
    "/runs/{run_id}/content-briefs/{content_brief_id}/review",
    response_model=list[StrategyReviewEntryResponse],
)
async def list_strategy_review(
    run_id: str,
    content_brief_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> list[StrategyReviewEntryResponse]:
    await get_run_with_reviewer_access(run_id, current_user, session)
    await _require_brief_in_run(session, run_id, content_brief_id)
    entries = await StrategyReviewStore(session).list_for_brief(content_brief_id)
    return [
        StrategyReviewEntryResponse(
            request_id=e.request_id,
            request_type=e.request_type,
            reason_or_kind=e.reason_or_kind,
            detail=e.detail,
            status=e.status,
            created_at=e.created_at,
        )
        for e in entries
    ]


@router.post(
    "/runs/{run_id}/content-briefs/{content_brief_id}/verify-compliance",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def verify_compliance(
    run_id: str,
    content_brief_id: str,
    payload: SpecialistOutputDeclaration,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> None:
    """Real enforcement of "specialists cannot silently change objectives, scope,
    methodology, or learning moves" -- a specialist declares what it produced and
    this either accepts it or returns 409 with the specific violations."""
    await get_run_with_reviewer_access(run_id, current_user, session)
    brief = await _require_brief_in_run(session, run_id, content_brief_id)
    try:
        enforce_content_brief_compliance(brief, payload)
    except SpecialistComplianceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "content_brief_compliance_violation", "violations": exc.violations},
        ) from exc


async def _require_brief_in_run(
    session: AsyncSession, run_id: str, content_brief_id: str,
) -> ContentBrief:
    brief = await ContentBriefStore(session).get(content_brief_id)
    if brief is None or brief.run_id != run_id:
        raise _content_brief_not_found()
    return brief


def _content_brief_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="content_brief_not_found")
