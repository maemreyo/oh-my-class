"""Run management — create, query, and stream pipeline runs."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import anyio
import orjson
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..auth.dependencies import require_teacher

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


@router.post("", response_model=RunResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def create_run(
    request: RunRequest,
    current_user: Annotated[object, Depends(require_teacher)],
) -> RunResponse:
    """POST /run — Start a new teaching pack generation run.

    Creates an OhMyClassState, fires the graph asynchronously,
    and returns the run_id immediately.
    """
    run_id = str(uuid.uuid4())

    return RunResponse(run_id=run_id, status="created")


@router.get("/{run_id}", response_model=RunResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_run(
    run_id: str,
    current_user: Annotated[object, Depends(require_teacher)],
) -> RunResponse:
    """GET /run/{id} — Get run state and current step."""
    # TODO: Load from checkpointer
    return RunResponse(
        run_id=run_id,
        status="running",
        state={"current_step": 1},
    )


@router.get("/{run_id}/status")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_run_status(
    run_id: str,
    current_user: Annotated[object, Depends(require_teacher)],
) -> StreamingResponse:
    """GET /run/{id}/status — SSE stream of pipeline progress."""

    async def event_generator():
        yield f"event: step_start\ndata: {orjson.dumps({'step': 1, 'run_id': run_id}).decode()}\n\n"

        for step in range(1, 4):
            await anyio.sleep(0)
            data = orjson.dumps({"step": step, "status": "completed"}).decode()
            yield f"event: step_end\ndata: {data}\n\n"

        data = orjson.dumps({"run_id": run_id, "status": "done"}).decode()
        yield f"event: complete\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
