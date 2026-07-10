from __future__ import annotations

from typing import Any, Final, Literal, TypedDict

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, Any]
type TeacherArtifactStatus = Literal[
    "passed",
    "regenerating",
    "failed",
    "skipped_due_dependency",
    "escalated",
]

_FAILED_SUMMARY: Final = "Artifact generation failed. Request edits to regenerate this item."
_SKIPPED_SUMMARY: Final = "Skipped because a required earlier artifact failed."
_ESCALATED_SUMMARY: Final = "Escalated for operator review."
_REGENERATING_SUMMARY: Final = "Generation is still in progress."
_PASSED_SUMMARY: Final = "Generated and ready for teacher review."
_UNSAFE_MARKERS: Final[tuple[str, ...]] = (
    "traceback",
    "api_key",
    "secret",
    "password",
    "provider",
    "stack",
    "prompt",
)


class ArtifactStatusItem(TypedDict):
    artifact_id: str
    artifact_type: str
    status: TeacherArtifactStatus
    summary: str
    teacher_action: str


def artifact_statuses_for_teacher(state: JsonObject) -> list[JsonObject]:
    requested_types = _requested_artifact_types(state)
    artifacts_by_type = _artifacts_by_type(_json_objects(state.get("artifact_references")))
    workflow_by_type = _workflow_by_type(_json_objects(state.get("artifact_workflow_states")))
    values: list[JsonObject] = []
    for artifact_type in requested_types:
        artifact = artifacts_by_type.get(artifact_type, {})
        workflow = workflow_by_type.get(artifact_type, {})
        item = _status_item(artifact_type, artifact, workflow)
        values.append(dict(item))
    return values


def unavailable_required_artifact_statuses(state: JsonObject) -> list[JsonObject]:
    unavailable = []
    for status in artifact_statuses_for_teacher(state):
        if status.get("status") != "passed":
            unavailable.append(status)
    return unavailable


def export_block_reason(unavailable: list[JsonObject]) -> str:
    artifact_types = ", ".join(str(item.get("artifact_type", "artifact")) for item in unavailable)
    return f"Export is blocked until these required artifacts are ready: {artifact_types}."


def _status_item(
    artifact_type: str,
    artifact: JsonObject,
    workflow: JsonObject,
) -> ArtifactStatusItem:
    raw_status = str(workflow.get("status", ""))
    match raw_status:
        case "passed":
            status: TeacherArtifactStatus = "passed"
            summary = _PASSED_SUMMARY
            action = "Review the generated artifact."
        case "failed":
            status = "failed"
            summary = _safe_failure_summary(workflow)
            action = "Request edits to regenerate this artifact."
        case "skipped":
            status = "skipped_due_dependency"
            summary = _SKIPPED_SUMMARY
            action = "Fix the failed dependency, then regenerate."
        case "escalated":
            status = "escalated"
            summary = _ESCALATED_SUMMARY
            action = "Wait for operator review or contact support."
        case "" if artifact:
            status = "passed"
            summary = _PASSED_SUMMARY
            action = "Review the generated artifact."
        case _:
            status = "regenerating"
            summary = _REGENERATING_SUMMARY
            action = "Wait for this artifact to finish generating."
    return {
        "artifact_id": _artifact_id(artifact_type, artifact, workflow),
        "artifact_type": artifact_type,
        "status": status,
        "summary": summary,
        "teacher_action": action,
    }


def _safe_failure_summary(workflow: JsonObject) -> str:
    value = workflow.get("error_summary")
    if not isinstance(value, str) or not value.strip():
        return _FAILED_SUMMARY
    lowered = value.lower()
    if len(value) > 160 or any(marker in lowered for marker in _UNSAFE_MARKERS):
        return _FAILED_SUMMARY
    return value.strip()


def _artifact_id(artifact_type: str, artifact: JsonObject, workflow: JsonObject) -> str:
    for source in (artifact, workflow):
        value = source.get("artifact_id")
        if isinstance(value, str) and value:
            return value
    return artifact_type


def _requested_artifact_types(state: JsonObject) -> list[str]:
    values = state.get("artifact_types")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    contract = _json_object(state.get("contract"))
    contract_values = contract.get("artifact_types")
    if isinstance(contract_values, list) and contract_values:
        return [str(value) for value in contract_values]
    artifacts = _json_objects(state.get("artifact_references"))
    artifact_types = [str(artifact.get("artifact_type", "")) for artifact in artifacts]
    return [artifact_type for artifact_type in artifact_types if artifact_type]


def _artifacts_by_type(artifacts: list[JsonObject]) -> dict[str, JsonObject]:
    return {str(artifact.get("artifact_type", "")): artifact for artifact in artifacts}


def _workflow_by_type(states: list[JsonObject]) -> dict[str, JsonObject]:
    return {str(state.get("artifact_type", "")): state for state in states}


def _json_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _json_objects(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
