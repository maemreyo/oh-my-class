"""Artifact retrieval — fetch generated artifacts for a run."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import Role, User  # noqa: TC001  needed at runtime for dependency injection
from ..exceptions import AuthorizationError, NotFoundError

router = APIRouter()


def _require_owner(run_data: dict[str, Any], user: User) -> None:
    if user.role == Role.ADMIN:
        return
    if run_data.get("teacher_id") != user.user_id:
        raise AuthorizationError(message="You do not have access to this run")


class ArtifactResponse(BaseModel):
    """Single artifact response."""

    artifact_id: str
    artifact_type: str
    title: str
    theme: str
    sections: list[dict[str, Any]]
    metadata: dict[str, Any]
    accessibility: dict[str, Any]
    rendered_html: str | None = None


def _extract_artifacts_from_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract artifacts from run state, generating IDs if needed."""
    artifacts = state.get("artifacts", [])
    result: list[dict[str, Any]] = []
    for i, artifact in enumerate(artifacts):
        a = dict(artifact)
        if "artifact_id" not in a:
            a["artifact_id"] = f"artifact-{i}"
        if "id" not in a:
            a["id"] = a["artifact_id"]
        result.append(a)
    return result


def _redact_teacher_only(artifact: dict[str, Any]) -> dict[str, Any]:
    """Remove teacher-only sections from artifact for student preview."""
    result = dict(artifact)
    sections = result.get("sections", [])
    result["sections"] = [
        s for s in sections
        if not s.get("teacher_only", False)
    ]
    return result


@router.get("/{run_id}/artifacts")  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_artifacts(
    run_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> list[ArtifactResponse]:
    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    _require_owner(run_data, current_user)

    state = run_data.get("state", {})
    artifacts = _extract_artifacts_from_state(state)

    return [ArtifactResponse(**_redact_teacher_only(a)) for a in artifacts]


@router.get("/{run_id}/artifacts/{artifact_id}")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_artifact(
    run_id: str,
    artifact_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ArtifactResponse:
    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    _require_owner(run_data, current_user)

    state = run_data.get("state", {})
    artifacts = _extract_artifacts_from_state(state)

    for artifact in artifacts:
        if artifact.get("artifact_id") == artifact_id or artifact.get("id") == artifact_id:
            return ArtifactResponse(**_redact_teacher_only(artifact))

    raise NotFoundError(message=f"Artifact {artifact_id} not found in run {run_id}")
