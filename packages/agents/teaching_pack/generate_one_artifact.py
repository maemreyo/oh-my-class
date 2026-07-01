from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from pydantic import ValidationError

from common.contracts.artifact import ArtifactContent

from packages.agents.sub_agents.content_creator.nodes import content_creator_node


class GenerateOneArtifactPayload(TypedDict):
    run_id: str
    artifact_generation_id: str
    artifact_type: str
    lesson_plan: dict[str, Any]
    research_brief: dict[str, Any]
    theme: str
    revision_feedback: NotRequired[str]
    dependency_artifacts: NotRequired[list[dict[str, Any]]]


class GenerateOneArtifactResult(TypedDict, total=False):
    artifact_chunks: list[dict[str, Any]]
    artifact_workflow_states: list[dict[str, Any]]


class ArtifactTypeMismatchError(ValueError):
    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"expected {expected}, got {actual}")


async def generate_one_artifact(payload: GenerateOneArtifactPayload) -> GenerateOneArtifactResult:
    artifact_type = payload["artifact_type"]
    generation_id = payload["artifact_generation_id"]
    result = await content_creator_node({
        "lesson_plan": payload["lesson_plan"],
        "research_bundle": payload["research_brief"],
        "artifact_types": [artifact_type],
        "theme": payload["theme"],
        "run_id": payload["run_id"],
        "current_step": 8,
        "artifacts": payload.get("dependency_artifacts", []),
        "revision_feedback": payload.get("revision_feedback", ""),
    })
    try:
        artifact = _single_artifact(result)
        if str(artifact.get("artifact_type", "")) != artifact_type:
            raise ArtifactTypeMismatchError(artifact_type, str(artifact.get("artifact_type", "")))
        parsed = ArtifactContent.model_validate(artifact).model_dump()
        artifact_id = str(artifact.get("artifact_id", f"{artifact_type}-1"))
    except (ArtifactTypeMismatchError, ValidationError, ValueError) as exc:
        return {"artifact_workflow_states": [_workflow_state(payload, "failed", exc)]}
    chunk = {**parsed, "artifact_id": artifact_id, "artifact_generation_id": generation_id}
    return {
        "artifact_chunks": [chunk],
        "artifact_workflow_states": [_workflow_state(
            payload,
            "passed",
            None,
            artifact_id=artifact_id,
        )],
    }


def _single_artifact(result: dict[str, Any]) -> dict[str, Any]:
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise ValueError("content_creator_node must return exactly one artifact")
    artifact = artifacts[0]
    if not isinstance(artifact, dict):
        raise ValueError("content_creator_node returned a non-object artifact")
    return artifact


def _workflow_state(
    payload: GenerateOneArtifactPayload,
    status: str,
    error: Exception | None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    artifact_type = payload["artifact_type"]
    state: dict[str, Any] = {
        "workflow_id": f"{payload['artifact_generation_id']}:{artifact_type}",
        "artifact_generation_id": payload["artifact_generation_id"],
        "artifact_id": artifact_id or artifact_type,
        "artifact_type": artifact_type,
        "status": status,
    }
    if error is not None:
        state["error_class"] = type(error).__name__
        state["error_summary"] = str(error)[:240]
    return state
