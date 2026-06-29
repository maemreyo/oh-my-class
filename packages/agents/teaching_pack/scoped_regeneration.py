from __future__ import annotations

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def merge_regenerated_artifacts(
    artifacts: list[JsonObject],
    gate_payload: JsonObject,
    generated: list[JsonObject],
) -> list[JsonObject]:
    rejections = scoped_rejections(artifacts, gate_payload)
    if not rejections:
        return generated
    rejected_ids = {str(item["artifact_id"]) for item in rejections}
    rejected_types = {str(item["artifact_type"]) for item in rejections}
    preserved = [
        artifact for artifact in artifacts
        if str(artifact.get("artifact_id", "")) not in rejected_ids
        and str(artifact.get("artifact_type", "")) not in rejected_types
    ]
    return [*preserved, *generated]


def rejected_artifact_types(artifacts: list[JsonObject], gate_payload: JsonObject) -> list[str]:
    types: list[str] = []
    for rejection in scoped_rejections(artifacts, gate_payload):
        artifact_type = str(rejection["artifact_type"])
        if artifact_type not in types:
            types.append(artifact_type)
    return types


def scoped_rejections(artifacts: list[JsonObject], gate_payload: JsonObject) -> list[JsonObject]:
    if gate_payload.get("rejection_type") != "scoped":
        return []
    raw_rejections = gate_payload.get("artifact_rejections")
    if not isinstance(raw_rejections, list):
        return []
    artifacts_by_id = {
        str(artifact.get("artifact_id", artifact.get("id", ""))): artifact
        for artifact in artifacts
    }
    rejections: list[JsonObject] = []
    for raw in raw_rejections:
        if not isinstance(raw, dict):
            continue
        artifact_id = str(raw.get("artifact_id", ""))
        artifact = artifacts_by_id.get(artifact_id)
        if artifact is None:
            continue
        rejections.append({
            "artifact_id": artifact_id,
            "artifact_type": str(artifact.get("artifact_type", "")),
            "reason": str(raw.get("reason", "")),
        })
    return rejections
