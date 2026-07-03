from __future__ import annotations

from typing import Any, Literal

type JsonObject = dict[str, Any]


def artifact_explanations_for_teacher(state: JsonObject, approval_mode: str) -> list[JsonObject]:
    reports = _reports_by_id(_json_object(state.get("quality_scores")).get("reports"))
    history = _healing_history_by_id(state.get("healing_context"))
    values: list[JsonObject] = []
    for artifact in _json_objects(state.get("artifacts")):
        artifact_id = _string_field(artifact, "artifact_id", _string_field(artifact, "id", "artifact"))
        artifact_type = _string_field(artifact, "artifact_type", _string_field(artifact, "type", "artifact"))
        report = reports.get(artifact_id, {})
        values.append({
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "judge_rationale": _judge_rationale(report),
            "revision_count": _revision_count(state, artifact),
            "healing_history": history.get(artifact_id, []),
            "approval_mode": approval_mode,
        })
    return values


def normalized_teacher_action(action: str) -> Literal["approve", "edit", "reject"] | str:
    match action:
        case "approve_selected":
            return "approve"
        case "reject_selected":
            return "reject"
        case _:
            return action


def is_scoped_teacher_action(gate_payload: JsonObject) -> bool:
    return gate_payload.get("action") in {"approve_selected", "reject_selected"}


def _reports_by_id(value: Any) -> dict[str, JsonObject]:
    return {
        _string_field(report, "artifact_id", ""): report
        for report in _json_objects(value)
        if _string_field(report, "artifact_id", "")
    }


def _healing_history_by_id(value: Any) -> dict[str, list[JsonObject]]:
    history = _json_object(value).get("history")
    result: dict[str, list[JsonObject]] = {}
    for item in _json_objects(history):
        artifact_id = _string_field(item, "artifact_id", "")
        if artifact_id:
            result.setdefault(artifact_id, []).append(item)
    return result


def _revision_count(state: JsonObject, artifact: JsonObject) -> int:
    artifact_value = artifact.get("revision_count")
    if isinstance(artifact_value, int):
        return artifact_value
    revisions_by_id = _json_object(state.get("artifact_revision_counts"))
    artifact_id = _string_field(artifact, "artifact_id", _string_field(artifact, "id", ""))
    mapped_value = revisions_by_id.get(artifact_id)
    if isinstance(mapped_value, int):
        return mapped_value
    value = state.get("artifact_generation_revision")
    if isinstance(value, int):
        return value
    return 0


def _judge_rationale(report: JsonObject) -> str:
    rationale = _string_field(report, "rationale", "")
    if rationale:
        return rationale
    if report.get("passed") is True:
        return "All configured quality checks passed for this artifact."
    issues = _json_objects(report.get("issues"))
    if issues:
        return _string_field(issues[0], "message", "Quality checks found issues.")
    return "Quality evidence is not available yet."


def _json_objects(value: Any) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _json_object(value: Any) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default
