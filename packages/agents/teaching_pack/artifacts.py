from __future__ import annotations

import re

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

_ANSWER_KEY_PATTERN = re.compile(
    r"\b(?:answer\s*(?:key|:)|correct\s*(?:answer|:)|solution:|đáp\s*án)",
    re.IGNORECASE,
)


def normalize_generated_artifacts(value: JsonValue | object, requested_types: list[str]) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    artifacts: list[JsonObject] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            continue
        artifact = dict(entry)
        artifact_type = _artifact_type(artifact, requested_types, index)
        artifact["artifact_type"] = artifact_type
        if not _has_text(artifact.get("artifact_id")):
            artifact["artifact_id"] = f"{artifact_type}-{index + 1}"
        artifact["sections"] = _normalize_sections(artifact.get("sections"))
        artifacts.append(artifact)
    return artifacts


def _artifact_type(artifact: JsonObject, requested_types: list[str], index: int) -> str:
    value = artifact.get("artifact_type")
    if isinstance(value, str) and value:
        return value
    if index < len(requested_types):
        return requested_types[index]
    return "lesson"


def _has_text(value: JsonValue) -> bool:
    return isinstance(value, str) and bool(value)


def _normalize_sections(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        return []
    sections: list[JsonValue] = []
    for section in value:
        if not isinstance(section, dict):
            sections.append(section)
            continue
        normalized = dict(section)
        if _ANSWER_KEY_PATTERN.search(str(normalized)):
            normalized["teacher_only"] = True
        sections.append(normalized)
    return sections
