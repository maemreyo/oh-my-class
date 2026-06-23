"""Run management — create, query, and stream pipeline runs."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def create_run():
    """POST /run — Start a new teaching pack generation run."""
    # TODO: Initialize OhMyClassState, invoke graph
    raise NotImplementedError


@router.get("/{run_id}")
async def get_run(run_id: str):
    """GET /run/{id} — Get run state and current step."""
    # TODO: Load from checkpointer
    raise NotImplementedError


@router.get("/{run_id}/status")
async def get_run_status(run_id: str):
    """GET /run/{id}/status — SSE stream of pipeline progress."""
    # TODO: Implement SSE stream
    raise NotImplementedError
