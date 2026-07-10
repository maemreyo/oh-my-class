from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from common.contracts.teaching_brief import TeachingBrief, materiality_reasons
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.backpressure import BackpressureConfig, check_backpressure
from services.gateway.models import RunStatus
from services.gateway.routers.teaching_pack_deps import (
    BACKPRESSURE_CONFIG,
    TEACHING_PACK_SESSION,
)
from services.gateway.routers.teaching_pack_helpers import hash_json
from services.gateway.run_creation import create_teaching_pack_run_record
from services.gateway.run_contract_setup import (
    ContractSetupGate,
    ContractSetupInput,
    ContractSetupReady,
    resolve_contract_setup,
)
from services.gateway.teaching_brief_store import StoredTeachingBrief, TeachingBriefStore
from services.gateway.teaching_pack_types import RunId, TeacherId

router = APIRouter()


class TeachingBriefResponse(TeachingBrief):
    brief_id: str
    planning_review_required: bool
    materiality_reasons: list[str]


class TeachingBriefContractPreviewResponse(TeachingBriefResponse):
    resolved_contract: dict[str, object] | None
    setup_gate: str | None


class TeachingBriefLaunchResponse(TeachingBriefResponse):
    run_id: str
    job_id: str | None
    status: RunStatus
    queued: bool


@router.post("/briefs", response_model=TeachingBriefResponse, status_code=status.HTTP_201_CREATED)
async def create_teaching_brief(
    brief: TeachingBrief,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingBriefResponse:
    stored = await TeachingBriefStore(session).create(
        brief_id=f"brief-{uuid4()}",
        teacher_id=current_user.user_id,
        brief=brief,
    )
    await session.commit()
    return _response(stored)


@router.get("/briefs/{brief_id}", response_model=TeachingBriefResponse)
async def get_teaching_brief(
    brief_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingBriefResponse:
    return _response(await _get_owned_brief(brief_id, current_user.user_id, session))


@router.put("/briefs/{brief_id}", response_model=TeachingBriefResponse)
async def autosave_teaching_brief(
    brief_id: str,
    brief: TeachingBrief,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingBriefResponse:
    stored = await TeachingBriefStore(session).replace(brief_id, current_user.user_id, brief)
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="brief_not_found")
    await session.commit()
    return _response(stored)


@router.get("/briefs/{brief_id}/contract-preview", response_model=TeachingBriefContractPreviewResponse)
async def preview_teaching_brief_contract(
    brief_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingBriefContractPreviewResponse:
    stored = await _get_owned_brief(brief_id, current_user.user_id, session)
    setup = resolve_contract_setup(ContractSetupInput(
        run_id=RunId(f"preview-{brief_id}"),
        teacher_id=TeacherId(current_user.user_id),
        raw_request=stored.brief.raw_request,
        class_info=_class_info_with_materiality(stored.brief),
    ))
    match setup:
        case ContractSetupReady(contract=contract):
            contract_json = contract.model_dump(mode="json")
            setup_gate = None
        case ContractSetupGate(gate_name=gate_name, contract=contract):
            contract_json = contract.model_dump(mode="json") if contract is not None else None
            setup_gate = gate_name
        case unreachable:
            from typing import assert_never

            assert_never(unreachable)
    return TeachingBriefContractPreviewResponse(
        **_response(stored).model_dump(),
        resolved_contract=contract_json,
        setup_gate=setup_gate,
    )


@router.post("/briefs/{brief_id}/launch", response_model=TeachingBriefLaunchResponse, status_code=status.HTTP_202_ACCEPTED)
async def launch_teaching_brief(
    brief_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
    bp_config: BackpressureConfig = BACKPRESSURE_CONFIG,
) -> TeachingBriefLaunchResponse:
    stored = await _get_owned_brief(brief_id, current_user.user_id, session)
    teacher_id = TeacherId(current_user.user_id)
    backpressure = await check_backpressure(teacher_id, session, config=bp_config)
    if not backpressure.allowed and not backpressure.queued:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=backpressure.reason)
    class_info = _class_info_with_materiality(stored.brief)
    result = await create_teaching_pack_run_record(
        session,
        teacher_id=teacher_id,
        raw_request=stored.brief.raw_request,
        class_info=class_info,
        request_hash=hash_json({"brief_id": brief_id, "brief": stored.brief.model_dump(mode="json")}),
        idempotency_key=None,
        eligible_at=backpressure.eligible_at,
    )
    await session.commit()
    return TeachingBriefLaunchResponse(
        **_response(stored).model_dump(),
        run_id=result.run_id,
        job_id=result.job_id,
        status=result.status,
        queued=result.queued,
    )


async def _get_owned_brief(brief_id: str, teacher_id: str, session: AsyncSession) -> StoredTeachingBrief:
    stored = await TeachingBriefStore(session).get(brief_id, teacher_id)
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="brief_not_found")
    return stored


def _response(stored: StoredTeachingBrief) -> TeachingBriefResponse:
    reasons = materiality_reasons(stored.brief)
    return TeachingBriefResponse(
        brief_id=stored.brief_id,
        **stored.brief.model_dump(mode="json"),
        planning_review_required=bool(reasons),
        materiality_reasons=reasons,
    )


def _class_info(brief: TeachingBrief) -> dict[str, object]:
    return {
        "topic": brief.topic,
        "grade": brief.grade,
        "subject": brief.subject,
        "locale": _locale_for(brief.target_language),
        "instruction_language": brief.instruction_language,
        "curriculum": brief.curriculum,
        "artifact_types": brief.artifact_types,
        "export_formats": brief.export_formats,
        "research_policy": brief.research_policy,
    }


def _class_info_with_materiality(brief: TeachingBrief) -> dict[str, object]:
    class_info = _class_info(brief)
    reasons = materiality_reasons(brief)
    if reasons:
        class_info["planning_review_reasons"] = reasons
    return class_info


def _locale_for(language: str) -> str:
    return "vi-VN" if language == "vi" else "en-US"
