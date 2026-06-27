"""Pipeline V2 run routes — create and resume.

The router merges sub-routers for streaming (pipeline_v2_stream) and
lifecycle (pipeline_v2_lifecycle) so that all pipeline-v2 routes are
registered under a single ``router`` object.
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.backpressure import BackpressureConfig, check_backpressure
from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_control_store import (
    GateResponseCreate,
    PipelineV2ControlStore,
    StaleGateResponseError,
)
from services.gateway.pipeline_v2_gate_registry import (
    GateValidationAccepted,
    PipelineV2GateAction,
    PipelineV2GateName,
    validate_gate_response,
)
from services.gateway.pipeline_v2_idempotency import (
    scoped_create_idempotency_key,
    scoped_resume_idempotency_key,
)
from services.gateway.pipeline_v2_job_store import PipelineV2JobStore, RunJobCreate
from services.gateway.pipeline_v2_models import RunJobKind
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.routers.pipeline_v2_deps import (
    BACKPRESSURE_CONFIG,
    PIPELINE_V2_SESSION,
    _default_backpressure_config,  # noqa: F401  re-exported for tests
    _get_run_with_ownership,
)
from services.gateway.routers.pipeline_v2_helpers import hash_json
from services.gateway.routers.pipeline_v2_lifecycle import lifecycle_router
from services.gateway.routers.pipeline_v2_schemas import (
    PipelineV2CreateRunRequest,
    PipelineV2ResumeAcceptedResponse,
    PipelineV2ResumeRequest,
    PipelineV2RunAcceptedResponse,
)
from services.gateway.routers.pipeline_v2_stream import stream_router
from services.gateway.run_creation import create_pipeline_v2_run_record

router = APIRouter()
router.include_router(stream_router)
router.include_router(lifecycle_router)


@router.post(
    "/run",
    response_model=PipelineV2RunAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_pipeline_v2_run(
    payload: PipelineV2CreateRunRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
    bp_config: BackpressureConfig = BACKPRESSURE_CONFIG,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PipelineV2RunAcceptedResponse:
    teacher_id = TeacherId(current_user.user_id)
    job_store = PipelineV2JobStore(session)
    request_hash = hash_json({
        "raw_request": payload.raw_request,
        "class_info": payload.class_info,
    })
    if idempotency_key is not None:
        scoped_idempotency_key = scoped_create_idempotency_key(teacher_id, idempotency_key)
        existing_job = await job_store.find_by_idempotency_key(scoped_idempotency_key)
        if existing_job is not None:
            if existing_job.payload.get("request_hash") != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_conflict",
                )
            if existing_job.payload.get("blocked_by_gate") is not None:
                return PipelineV2RunAcceptedResponse(
                    run_id=existing_job.run_id,
                    job_id=None,
                    status=RunStatus.AWAITING_APPROVAL,
                )
            return PipelineV2RunAcceptedResponse(
                run_id=existing_job.run_id,
                job_id=existing_job.job_id,
                status=RunStatus.PENDING,
            )

    bp = await check_backpressure(teacher_id, session, config=bp_config)
    if not bp.allowed and not bp.queued:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=bp.reason,
        )

    result = await create_pipeline_v2_run_record(
        session,
        teacher_id=teacher_id,
        raw_request=payload.raw_request,
        class_info=payload.class_info,
        request_hash=request_hash,
        idempotency_key=scoped_create_idempotency_key(teacher_id, idempotency_key)
        if idempotency_key is not None
        else None,
        eligible_at=bp.eligible_at,
    )
    await session.commit()
    return PipelineV2RunAcceptedResponse(
        run_id=result.run_id,
        job_id=result.job_id,
        status=result.status,
        queued=result.queued,
    )


@router.post(
    "/run/{run_id}/resume",
    response_model=PipelineV2ResumeAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resume_pipeline_v2_run(
    run_id: str,
    payload: PipelineV2ResumeRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PipelineV2ResumeAcceptedResponse:
    validation = validate_gate_response(payload.gate_name, payload.action)
    match validation:
        case GateValidationAccepted():
            pass
        case rejected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=rejected.reason,
            )

    await _get_run_with_ownership(run_id, current_user, session)
    typed_run_id = RunId(run_id)
    teacher_id = TeacherId(current_user.user_id)

    resume_payload = {"action": validation.action.value, **payload.response}
    request_hash = hash_json({
        "gate_id": payload.gate_id,
        "gate_name": payload.gate_name,
        "response": resume_payload,
    })
    job_store = PipelineV2JobStore(session)
    if idempotency_key is not None:
        scoped_idempotency_key = scoped_resume_idempotency_key(
            typed_run_id,
            teacher_id,
            idempotency_key,
        )
        existing_job = await job_store.find_by_idempotency_key(scoped_idempotency_key)
        if existing_job is not None:
            if existing_job.payload.get("request_hash") != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_conflict",
                )
            response_id = existing_job.payload.get("response_id")
            return PipelineV2ResumeAcceptedResponse(
                run_id=existing_job.run_id,
                response_id=str(response_id),
                job_id=existing_job.job_id,
            )

    response_id = f"response-{uuid4()}"
    try:
        control_store = PipelineV2ControlStore(session)
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=response_id,
            gate_id=payload.gate_id,
            run_id=typed_run_id,
            teacher_id=teacher_id,
            response_json=resume_payload,
        ))
        if (
            validation.action is PipelineV2GateAction.EDIT
            and validation.gate_name is PipelineV2GateName.CONTRACT_CONFIRMATION
        ):
            edits = payload.response.get("edits")
            if isinstance(edits, dict):
                next_revision = await control_store.apply_contract_edits(typed_run_id, edits)
                resume_payload = {**resume_payload, "contract_revision": next_revision}
    except StaleGateResponseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="stale_gate") from exc
    job = await job_store.enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=typed_run_id,
        kind=RunJobKind.RESUME,
        idempotency_key=(
            scoped_resume_idempotency_key(typed_run_id, teacher_id, idempotency_key)
            if idempotency_key is not None
            else f"resume:{response_id}"
        ),
        payload={
            "response_id": response_id,
            "request_hash": request_hash,
            "resume_payload": resume_payload,
        },
    ))
    await session.commit()
    return PipelineV2ResumeAcceptedResponse(
        run_id=job.run_id,
        response_id=response_id,
        job_id=job.job_id,
    )
