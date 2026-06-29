from __future__ import annotations

import re
from copy import deepcopy
from typing import TYPE_CHECKING

from common.contracts.artifact import ArtifactContent
from common.contracts.quality import HealingStrategy, QualityFailureClass
from services.gateway.quality_gates import classify_healing, validate_artifact_content

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import JsonObject, JsonValue

_ANSWER_KEY_PATTERN = re.compile(
    r"\b(?:answer key|answer:|correct:|solution:)",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_STUDENT_PII_PATTERN = re.compile(r"\b(?:student|pupil)\s+(?:name|email|phone)\b", re.IGNORECASE)


class UnrepairableArtifactError(RuntimeError):
    def __init__(self, failure_class: QualityFailureClass) -> None:
        super().__init__(failure_class.value)


def try_heal_artifact(artifact_id: str, artifact: ArtifactContent) -> ArtifactContent | None:
    report = validate_artifact_content(artifact_id, artifact)
    if report.passed:
        return artifact
    healed = artifact
    repaired = False
    for issue in report.issues:
        try:
            healed = heal_artifact(healed, issue.failure_class)
        except UnrepairableArtifactError:
            continue
        repaired = True
    if not repaired:
        return None
    healed_report = validate_artifact_content(artifact_id, healed)
    if healed_report.passed:
        return healed
    return None


def heal_artifact(
    artifact: ArtifactContent,
    failure_class: QualityFailureClass,
) -> ArtifactContent:
    decision = classify_healing(failure_class)
    match decision.strategy:
        case HealingStrategy.SCHEMA_REPAIR:
            return repair_schema(artifact.model_dump())
        case HealingStrategy.ANSWER_KEY_REPAIR:
            return repair_answer_key_leakage(artifact)
        case HealingStrategy.PII_REMOVAL:
            return remove_pii(artifact)
        case HealingStrategy.ACCESSIBILITY_REPAIR:
            return repair_accessibility(artifact)
        case (
            HealingStrategy.PRESENTATION_REPAIR
            | HealingStrategy.REGENERATE_ARTIFACT
            | HealingStrategy.RESEARCH_ENRICHMENT
            | HealingStrategy.REPLAN_BLUEPRINT
            | HealingStrategy.ESCALATE
        ):
            raise UnrepairableArtifactError(failure_class)


def repair_schema(raw_artifact: JsonObject) -> ArtifactContent:
    repaired = {
        **raw_artifact,
        "artifact_type": raw_artifact.get("artifact_type", "lesson"),
        "theme": raw_artifact.get("theme", "default"),
        "title": str(raw_artifact.get("title", "Untitled Artifact")),
        "sections": _sections(raw_artifact.get("sections")),
        "metadata": _object(raw_artifact.get("metadata")),
        "accessibility": _object(raw_artifact.get("accessibility")) | {"language": "en"},
    }
    return ArtifactContent.model_validate(repaired)


def repair_answer_key_leakage(artifact: ArtifactContent) -> ArtifactContent:
    sections = deepcopy(artifact.sections)
    for section in sections:
        if section.get("teacher_only") is True:
            continue
        if _ANSWER_KEY_PATTERN.search(str(section)):
            section["teacher_only"] = True
    return artifact.model_copy(update={"sections": sections})


def remove_pii(artifact: ArtifactContent) -> ArtifactContent:
    repaired = _redact_json(artifact.model_dump())
    return ArtifactContent.model_validate(repaired)


def repair_accessibility(artifact: ArtifactContent) -> ArtifactContent:
    accessibility = {
        **artifact.accessibility,
        "language": artifact.accessibility.get("language", "en"),
    }
    return artifact.model_copy(update={"accessibility": accessibility})


def _sections(value: JsonValue | None) -> list[JsonObject]:
    if isinstance(value, list):
        sections = [section for section in value if isinstance(section, dict)]
        if sections:
            return sections
    return [{"content": "oh-my-class content"}]


def _object(value: JsonValue | None) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _redact_json(value: JsonValue) -> JsonValue:
    match value:
        case str():
            without_email = _EMAIL_PATTERN.sub("[redacted]", value)
            return _STUDENT_PII_PATTERN.sub("student information", without_email)
        case list():
            return [_redact_json(item) for item in value]
        case dict():
            return {key: _redact_json(item) for key, item in value.items()}
        case int() | float() | bool() | None:
            return value
