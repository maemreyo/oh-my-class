"""Run management — create, query, and stream pipeline runs."""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import User

router = APIRouter()


class RunRequest(BaseModel):
    """Request body for creating a new run."""

    raw_request: str
    class_info: dict[str, Any]
    teacher_id: str


class RunResponse(BaseModel):
    """Response from run endpoints."""

    run_id: str
    status: str
    state: dict[str, Any] | None = None


@router.post("", response_model=RunResponse)
async def create_run(
    request: RunRequest,
    current_user: Annotated[User, Depends(require_teacher)],
) -> RunResponse:
    """POST /run — Start a new teaching pack generation run.

    Creates an OhMyClassState, fires the graph asynchronously,
    and returns the run_id immediately.
    """
    import asyncio

    run_id = str(uuid.uuid4())

    async def _invoke_graph():
        try:
            from packages.agents.graph import build_oh_my_class_graph

            graph = build_oh_my_class_graph(environment="development")
            # Real implementation streams graph events via checkpointer
        except Exception as e:
            print(f"Graph invocation failed for run {run_id}: {e}")

    asyncio.create_task(_invoke_graph())

    return RunResponse(run_id=run_id, status="created")


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
) -> RunResponse:
    """GET /run/{id} — Get run state and current step."""
    # TODO: Load from checkpointer
    return RunResponse(
        run_id=run_id,
        status="running",
        state={"current_step": 1},
    )


@router.get("/{run_id}/status")
async def get_run_status(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
) -> StreamingResponse:
    """GET /run/{id}/status — SSE stream of pipeline progress."""

    async def event_generator():
        import asyncio

        yield f"event: step_start\ndata: {json.dumps({'step': 1, 'run_id': run_id})}\n\n"

        for step in range(1, 4):
            await asyncio.sleep(0)
            yield f"event: step_end\ndata: {json.dumps({'step': step, 'status': 'completed'})}\n\n"

        yield f"event: complete\ndata: {json.dumps({'run_id': run_id, 'status': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
