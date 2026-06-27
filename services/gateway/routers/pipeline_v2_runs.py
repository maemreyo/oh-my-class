from __future__ import annotations

from typing import Annotated
from uuid import uuid4

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User  # noqa: TC001
from services.gateway.auth.ownership import check_run_owner
from services.gateway.backpressure import BackpressureConfig, check_backpressure
from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_control_store import (
    GateResponseCreate,
    PipelineV2ControlStore,
    StaleGateResponseError,
)
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
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
from services.gateway.pipeline_v2_models import PipelineV2EventVisibility, RunJobKind
from services.gateway.pipeline_v2_store import (
    InvalidRunStatusTransitionError,
    PipelineV2EventCreate,
    PipelineV2RunStore,
    PipelineV2StatusTransition,
)
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.routers.pipeline_v2_helpers import format_event_stream, hash_json
from services.gateway.routers.pipeline_v2_schemas import (
    PipelineV2CancelResponse,
    PipelineV2CreateRunRequest,
    PipelineV2DeleteResponse,
    PipelineV2RestoreResponse,
    PipelineV2ResumeAcceptedResponse,
    PipelineV2ResumeRequest,
    PipelineV2RunAcceptedResponse,
)
from services.gateway.run_creation import create_pipeline_v2_run_record
from services.gateway.soft_delete import is_run_deleted, restore_run, soft_delete_run

router = APIRouter()
PIPELINE_V2_SESSION = Depends(get_pipeline_v2_session)


def _default_backpressure_config() -> BackpressureConfig:
    return BackpressureConfig()


BACKPRESSURE_CONFIG = Depends(_default_backpressure_config)


async def _get_run_with_ownership(
    run_id: str,
    user: User,
    session: AsyncSession,
):
    """Fetch a run enforcing cross-tenant ownership rules.

    SYSTEM_ADMIN bypasses the teacher_id filter; all other roles must own
    the run.  Returns the run or raises 403/404.
    """
    typed_run_id = RunId(run_id)
    store = PipelineV2RunStore(session)

    if user.role == Role.SYSTEM_ADMIN:
        run = await store.get_run_by_id(typed_run_id)
    else:
        run = await store.get_run(typed_run_id, TeacherId(user.user_id))

    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")

    if await is_run_deleted(run_id, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")

    if not await check_run_owner(run_id, user, session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_run_owner")

    return run

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


@router.post("/run/{run_id}/cancel", response_model=PipelineV2CancelResponse)
async def cancel_pipeline_v2_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> PipelineV2CancelResponse:
    await _get_run_with_ownership(run_id, current_user, session)
    typed_run_id = RunId(run_id)
    run_store = PipelineV2RunStore(session)

    cancelled_jobs = await PipelineV2JobStore(session).cancel_run_jobs(typed_run_id)
    try:
        await run_store.transition_status(PipelineV2StatusTransition(
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
    await run_store.write_event(PipelineV2EventCreate(
        run_id=typed_run_id,
        event_name="pipeline_v2.run.cancelled",
        visibility=PipelineV2EventVisibility.TEACHER,
        payload={
            "actor_id": current_user.user_id,
            "reason": "teacher_cancelled",
            "cancelled_jobs": cancelled_jobs,
        },
    ))
    await session.commit()
    return PipelineV2CancelResponse(
        run_id=run_id,
        status=RunStatus.CANCELLED,
        cancelled_jobs=cancelled_jobs,
    )


@router.get("/run/{run_id}/status")
async def stream_pipeline_v2_status(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    last_event_id_query: Annotated[str | None, Query(alias="last_event_id")] = None,
    replay_only: bool = False,
) -> StreamingResponse:
    await _get_run_with_ownership(run_id, current_user, session)
    typed_run_id = RunId(run_id)
    store = PipelineV2RunStore(session)

    requested_last_event_id = last_event_id if last_event_id is not None else last_event_id_query
    after_sequence = int(requested_last_event_id) if requested_last_event_id is not None else 0
    events = await store.replay_events(typed_run_id, after_sequence=after_sequence)

    async def event_generator():
        last_sequence = after_sequence
        for event in events:
            if event.visibility is PipelineV2EventVisibility.TEACHER:
                last_sequence = max(last_sequence, event.sequence)
                yield format_event_stream(event)
        if replay_only:
            return
        while True:
            await anyio.sleep(1)
            live_events = await store.replay_events(typed_run_id, after_sequence=last_sequence)
            for event in live_events:
                last_sequence = max(last_sequence, event.sequence)
                if event.visibility is PipelineV2EventVisibility.TEACHER:
                    yield format_event_stream(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete(
    "/run/{run_id}",
    response_model=PipelineV2DeleteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_pipeline_v2_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> PipelineV2DeleteResponse:
    """Soft-delete a run.  The run is hidden from normal queries but
    retained for the configured retention period before hard purge."""
    await _get_run_with_ownership(run_id, current_user, session)
    await soft_delete_run(run_id, current_user.user_id, session)
    await session.commit()
    return PipelineV2DeleteResponse(run_id=run_id, deleted=True)


@router.post(
    "/run/{run_id}/restore",
    response_model=PipelineV2RestoreResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def restore_pipeline_v2_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = PIPELINE_V2_SESSION,
) -> PipelineV2RestoreResponse:
    """Restore a soft-deleted run, making it visible again."""
    typed_run_id = RunId(run_id)
    store = PipelineV2RunStore(session)
    if current_user.role == Role.SYSTEM_ADMIN:
        run = await store.get_run_by_id(typed_run_id)
    else:
        run = await store.get_run(typed_run_id, TeacherId(current_user.user_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")
    await restore_run(run_id, current_user.user_id, session)
    await session.commit()
    return PipelineV2RestoreResponse(run_id=run_id, restored=True)
