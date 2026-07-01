from __future__ import annotations

from typing import Any

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, Any]


def skipped_dependents(
    generation_id: str,
    requested_types: list[str],
    failed_types: set[str],
    dependencies: dict[str, tuple[str, ...]],
) -> list[JsonObject]:
    skipped: list[JsonObject] = []
    for artifact_type in requested_types:
        artifact_dependencies = dependencies.get(artifact_type, ())
        if failed_types.intersection(artifact_dependencies):
            skipped.append({
                "workflow_id": f"{generation_id}:{artifact_type}",
                "artifact_generation_id": generation_id,
                "artifact_id": artifact_type,
                "artifact_type": artifact_type,
                "status": "skipped",
                "error_summary": "required dependency failed",
            })
    return skipped


def sort_artifacts(artifacts: list[JsonObject], requested_types: list[str]) -> list[JsonObject]:
    positions = {artifact_type: index for index, artifact_type in enumerate(requested_types)}
    return sorted(
        artifacts,
        key=lambda artifact: (
            positions.get(str(artifact.get("artifact_type", "")), len(positions)),
            str(artifact.get("artifact_id", artifact.get("id", ""))),
        ),
    )


def all_artifact_types(artifacts: list[JsonObject]) -> list[str]:
    values: list[str] = []
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type", ""))
        if artifact_type and artifact_type not in values:
            values.append(artifact_type)
    return values


def with_dependents(
    seed_types: list[str],
    requested_types: list[str],
    dependencies: dict[str, tuple[str, ...]],
) -> list[str]:
    affected = set(seed_types)
    changed = True
    while changed:
        changed = False
        for artifact_type in requested_types:
            artifact_dependencies = dependencies.get(artifact_type, ())
            if artifact_type not in affected and affected.intersection(artifact_dependencies):
                affected.add(artifact_type)
                changed = True
    return [artifact_type for artifact_type in requested_types if artifact_type in affected]


def json_object(value: JsonValue | object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def json_objects(value: JsonValue | object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def any_json_object(value: JsonValue | object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def any_json_objects(value: JsonValue | object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default


def string_value(value: JsonValue | object) -> str:
    if isinstance(value, str):
        return value
    return ""
