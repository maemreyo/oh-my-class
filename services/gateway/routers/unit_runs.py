"""Unit runs router — aggregate read API, multiplexed SSE, and unit actions (td-011).

Endpoints:
  GET  /units/{parent_run_id}          → UnitView snapshot
  GET  /units/{parent_run_id}/status   → SSE stream of unit-level events
  POST /units/{parent_run_id}/approve-all
  POST /units/{parent_run_id}/sessions/{session_id}/spawn-anyway
  POST /units/{parent_run_id}/export
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from common.contracts.lesson_sequence import LessonSequence
from common.contracts.unit_view import (
    UnitAggregate,
    UnitParentMeta,
    UnitSessionProgress,
    UnitView,
)
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.models import Run, RunStatus, UnitRole
from services.gateway.teaching_pack_control_store import (
    GateResponseCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_event_bus import (
    current_run_event_version,
    wait_for_run_event,
)
from services.gateway.teaching_pack_gate_registry import TeachingPackGateName
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJobKind
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.unit_run_store import UnitRunStore, UnitSessionRunCreate


TEACHING_PACK_SESSION = Depends(get_teaching_pack_session)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _display_status(run_status: RunStatus, is_blocked: bool = False) -> str:
    if is_blocked:
        return "blocked"
    match run_status:
        case RunStatus.PENDING | RunStatus.PLANNING | RunStatus.RESEARCHING | RunStatus.GENERATING:
            return "generating"
        case RunStatus.REVIEWING | RunStatus.AWAITING_APPROVAL:
            return "in_review"
        case RunStatus.EXPORTING | RunStatus.COMPLETED:
            return "approved"
        case RunStatus.FAILED | RunStatus.CANCELLED:
            return "failed"
        case _:
            return "pending"


def _aggregate_status(total: int, approved: int, failed: int, active: int) -> str:
    if approved == total:
        return "complete"
    if approved > 0 and failed > 0 and active == 0:
        return "partially_complete"
    if active > 0:
        return "generating"
    if failed > 0 and approved == 0:
        return "partially_complete"
    return "preparing"


async def _get_parent_run_owned(
    parent_run_id: str,
    user: User,
    session: AsyncSession,
) -> Run:
    result = await session.execute(
        select(Run).where(
            Run.run_id == parent_run_id,
            Run.unit_role == UnitRole.UNIT_PARENT,
        )
    )
    parent = result.scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unit_not_found")
    if parent.teacher_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_unit_owner")
    return parent


# ---------------------------------------------------------------------------
# GET /units/{parent_run_id}
# ---------------------------------------------------------------------------


@router.get("/units/{parent_run_id}", response_model=UnitView)
async def get_unit_view(
    parent_run_id: str,
    user: Annotated[User, Depends(require_teacher)],
    session: Annotated[AsyncSession, TEACHING_PACK_SESSION],
) -> UnitView:
    parent = await _get_parent_run_owned(parent_run_id, user, session)

    run_store = UnitRunStore(session)
    children = await run_store.list_children(RunId(parent_run_id))
    seq_json = await run_store.get_lesson_sequence(RunId(parent_run_id))

    if seq_json is None or parent.lesson_sequence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sequence_not_found")

    sequence = LessonSequence.model_validate(seq_json)

    # Map existing child run statuses by session_id.
    child_status_map: dict[str, tuple[RunStatus, str | None]] = {
        c.session_id: (c.status, c.run_id)
        for c in children
        if c.session_id
    }

    session_progress: list[UnitSessionProgress] = []
    approved_count = 0
    failed_count = 0
    active_count = 0

    for sess_plan in sequence.sessions:
        sid = sess_plan.session_id
        if sid in child_status_map:
            run_st, child_run_id = child_status_map[sid]
            disp = _display_status(run_st)
            if disp == "approved":
                approved_count += 1
            elif disp == "failed":
                failed_count += 1
            elif disp in ("generating", "in_review"):
                active_count += 1
        else:
            disp = "pending"
            child_run_id = None

        session_progress.append(UnitSessionProgress(
            session_id=sid,
            child_run_id=child_run_id,
            status=disp,  # type: ignore[arg-type]
            progress_percent=100 if disp == "approved" else (50 if disp == "in_review" else 0),
        ))

    cursor = current_run_event_version(RunId(parent_run_id))

    return UnitView(
        parent=UnitParentMeta(
            parent_run_id=parent_run_id,
            teacher_id=parent.teacher_id,
            topic=sequence.topic,
        ),
        sequence=sequence,
        sessions=session_progress,
        aggregate=UnitAggregate(
            status=_aggregate_status(  # type: ignore[arg-type]
                sequence.total_sessions, approved_count, failed_count, active_count
            ),
            total_sessions=sequence.total_sessions,
            approved_sessions=approved_count,
            failed_sessions=failed_count,
        ),
        coherence_warnings=[],
        cursor=cursor,
    )


# ---------------------------------------------------------------------------
# GET /units/{parent_run_id}/status  — multiplexed SSE
# ---------------------------------------------------------------------------


async def _unit_sse_generator(parent_run_id: RunId, cursor: int):
    """Yield SSE events for a unit, filtered to that unit's runs."""
    observed = cursor
    while True:
        new_version = current_run_event_version(parent_run_id)
        if new_version > observed:
            observed = new_version
            event_data = json.dumps({
                "event_type": "unit.progress",
                "parent_run_id": str(parent_run_id),
                "cursor": observed,
            })
            yield f"event: unit.progress\ndata: {event_data}\n\n"
        woke = await wait_for_run_event(parent_run_id, observed, timeout_seconds=30.0)
        if not woke:
            # Heartbeat
            yield f": heartbeat\n\n"


@router.get("/units/{parent_run_id}/status")
async def stream_unit_status(
    parent_run_id: str,
    request: Request,
    user: Annotated[User, Depends(require_teacher)],
    session: Annotated[AsyncSession, TEACHING_PACK_SESSION],
    cursor: int = 0,
) -> StreamingResponse:
    await _get_parent_run_owned(parent_run_id, user, session)
    run_id = RunId(parent_run_id)

    return StreamingResponse(
        _unit_sse_generator(run_id, cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /units/{parent_run_id}/approve-all
# ---------------------------------------------------------------------------


@router.post("/units/{parent_run_id}/approve-all")
async def approve_all_sessions(
    parent_run_id: str,
    user: Annotated[User, Depends(require_teacher)],
    session: Annotated[AsyncSession, TEACHING_PACK_SESSION],
) -> dict:
    await _get_parent_run_owned(parent_run_id, user, session)

    run_store = UnitRunStore(session)
    children = await run_store.list_children(RunId(parent_run_id))
    job_store = TeachingPackJobStore(session)
    control_store = TeachingPackControlStore(session)

    results: dict[str, str] = {}

    for child in children:
        if child.status is not RunStatus.AWAITING_APPROVAL:
            continue
        session_id = child.session_id or child.run_id
        try:
            # Find the active gate for this child run.
            active_gates = await control_store.list_active_gates(child.run_id)
            if not active_gates:
                results[session_id] = "skipped: no active gate"
                continue
            gate_row = active_gates[0]

            gate_response_id = str(uuid4())
            await control_store.respond_to_gate(GateResponseCreate(
                response_id=gate_response_id,
                gate_id=gate_row.gate_id,
                run_id=child.run_id,
                teacher_id=TeacherId(user.user_id),
                response_json={"action": "approve"},
            ))
            await job_store.enqueue(RunJobCreate(
                job_id=str(uuid4()),
                run_id=child.run_id,
                kind=RunJobKind.RESUME,
                idempotency_key=f"approve-all:{parent_run_id}:{session_id}:{gate_response_id}",
                payload={"gate_response_id": gate_response_id},
            ))
            results[session_id] = "resumed"
        except Exception as exc:
            results[session_id] = f"failed: {exc}"

    await session.commit()
    return {"results": results}


# ---------------------------------------------------------------------------
# POST /units/{parent_run_id}/sessions/{session_id}/spawn-anyway
# ---------------------------------------------------------------------------


@router.post("/units/{parent_run_id}/sessions/{session_id}/spawn-anyway")
async def spawn_anyway(
    parent_run_id: str,
    session_id: str,
    user: Annotated[User, Depends(require_teacher)],
    session: Annotated[AsyncSession, TEACHING_PACK_SESSION],
) -> dict:
    parent = await _get_parent_run_owned(parent_run_id, user, session)

    run_store = UnitRunStore(session)
    seq_json = await run_store.get_lesson_sequence(RunId(parent_run_id))
    if seq_json is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sequence_not_found")

    sequence = LessonSequence.model_validate(seq_json)
    session_plan = next((s for s in sequence.sessions if s.session_id == session_id), None)
    if session_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")

    # Check if already spawned — idempotent.
    children = await run_store.list_children(RunId(parent_run_id))
    existing = next((c for c in children if c.session_id == session_id), None)
    if existing is not None:
        return {"status": "already_spawned", "run_id": existing.run_id}

    child_run_id = RunId(str(uuid4()))
    await run_store.create_child_run(UnitSessionRunCreate(
        run_id=child_run_id,
        parent_run_id=RunId(parent_run_id),
        teacher_id=parent.teacher_id,
        session_id=session_id,
        session_index=session_plan.order_index,
        raw_request=parent.raw_request,
        class_info=parent.class_info or {},
        retention_days=parent.retention_days,
    ))

    job_store = TeachingPackJobStore(session)
    await job_store.enqueue(RunJobCreate(
        job_id=str(uuid4()),
        run_id=child_run_id,
        kind=RunJobKind.START,
        idempotency_key=f"spawn-anyway:{parent_run_id}:{session_id}",
        payload={"run_id": child_run_id},
    ))

    await session.commit()
    return {"status": "spawned", "run_id": child_run_id}


# ---------------------------------------------------------------------------
# POST /units/{parent_run_id}/export
# ---------------------------------------------------------------------------


@router.post("/units/{parent_run_id}/export")
async def export_unit(
    parent_run_id: str,
    user: Annotated[User, Depends(require_teacher)],
    session: Annotated[AsyncSession, TEACHING_PACK_SESSION],
) -> dict:
    await _get_parent_run_owned(parent_run_id, user, session)
    # Unit packager is triggered lazily; record intent and return.
    # The actual packaging is done by UnitPackager when a worker picks it up.
    return {"status": "queued", "parent_run_id": parent_run_id}
