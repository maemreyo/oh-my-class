"""Artifact retrieval — fetch generated artifacts for a run."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{run_id}/artifacts")  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_artifacts(run_id: str):
    """GET /run/{id}/artifacts — List all artifacts for a run."""
    # TODO: Query artifacts from state/checkpointer
    raise NotImplementedError


@router.get("/{run_id}/artifacts/{artifact_id}")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_artifact(run_id: str, artifact_id: str):
    """GET /run/{id}/artifacts/{id} — Get specific artifact content."""
    # TODO: Retrieve specific artifact by ID
    raise NotImplementedError
