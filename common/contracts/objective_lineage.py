from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class ObjectiveImportance(StrEnum):
    CORE = "core"
    SUPPORTING = "supporting"
    EXTENSION = "extension"


class ObjectiveAssessmentIntent(StrEnum):
    NONE = "none"
    FORMATIVE = "formative"
    SUMMATIVE = "summative"
    EXAM_PREP = "exam_prep"
    DIAGNOSTIC = "diagnostic"


class BlueprintEditIntent(StrEnum):
    AUTO_DETECT = "auto_detect"
    WORDING_ONLY = "wording_only"
    LEARNING_TARGET_CHANGE = "learning_target_change"


class ObjectiveLineageModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class NormalizedLearningObjective(ObjectiveLineageModel):
    objective_id: str = Field(min_length=1, max_length=80)
    objective_revision: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    bloom_level: str = Field(min_length=1, max_length=40)
    importance: ObjectiveImportance
    assessable: bool
    assessment_intent: ObjectiveAssessmentIntent
    inference_reason: str = Field(min_length=1, max_length=240)


class ObjectiveNormalizationResult(ObjectiveLineageModel):
    blueprint_revision_id: str = Field(min_length=1, max_length=80)
    objectives: tuple[NormalizedLearningObjective, ...] = Field(min_length=1)


class ObjectiveRevisionDecision(ObjectiveLineageModel):
    materiality: str = Field(min_length=1, max_length=40)
    strategy_invalidated: bool
    reason: str = Field(min_length=1, max_length=240)


_WORD_RE: Final = re.compile(r"[a-z0-9]+")


def normalize_learning_objectives(
    learning_objectives: list[dict[str, str | bool]],
    *,
    blueprint_revision_id: str = "bp-rev-1",
) -> ObjectiveNormalizationResult:
    objectives = tuple(_normalized_objective(item) for item in learning_objectives)
    return ObjectiveNormalizationResult(blueprint_revision_id=blueprint_revision_id, objectives=objectives)


def compare_objective_revisions(
    previous: ObjectiveNormalizationResult,
    current: ObjectiveNormalizationResult,
    *,
    edit_intent: BlueprintEditIntent = BlueprintEditIntent.AUTO_DETECT,
) -> ObjectiveRevisionDecision:
    if edit_intent is BlueprintEditIntent.WORDING_ONLY:
        return ObjectiveRevisionDecision(materiality="cosmetic", strategy_invalidated=False, reason="edit marked wording-only")
    if edit_intent is BlueprintEditIntent.LEARNING_TARGET_CHANGE:
        return ObjectiveRevisionDecision(materiality="semantic", strategy_invalidated=True, reason="edit marked learning-target change")
    if _semantic_keys(previous) == _semantic_keys(current):
        return ObjectiveRevisionDecision(materiality="cosmetic", strategy_invalidated=False, reason="semantic objective keys unchanged")
    return ObjectiveRevisionDecision(materiality="semantic", strategy_invalidated=True, reason="semantic objective keys changed")


def _normalized_objective(item: dict[str, str | bool]) -> NormalizedLearningObjective:
    description = str(item.get("description", "")).strip()
    bloom_level = str(item.get("bloom_level", "understand"))
    assessment_method = str(item.get("assessment_method", "")).strip()
    importance = _importance(item, bloom_level)
    assessable = _assessable(item, assessment_method)
    intent = _assessment_intent(item, assessment_method, assessable)
    semantic_key = _semantic_key(description, bloom_level)
    return NormalizedLearningObjective(
        objective_id=str(item.get("objective_id") or f"obj-{_digest(semantic_key)[:10]}"),
        objective_revision=str(item.get("objective_revision") or f"rev-{_digest(semantic_key)[:8]}"),
        description=description,
        bloom_level=bloom_level,
        importance=importance,
        assessable=assessable,
        assessment_intent=intent,
        inference_reason=_inference_reason(item),
    )


def _importance(item: dict[str, str | bool], bloom_level: str) -> ObjectiveImportance:
    value = item.get("importance")
    if isinstance(value, str) and value in ObjectiveImportance:
        return ObjectiveImportance(value)
    return ObjectiveImportance.EXTENSION if bloom_level in {"evaluate", "create"} else ObjectiveImportance.CORE


def _assessable(item: dict[str, str | bool], assessment_method: str) -> bool:
    value = item.get("assessable")
    if isinstance(value, bool):
        return value
    return bool(assessment_method)


def _assessment_intent(
    item: dict[str, str | bool],
    assessment_method: str,
    assessable: bool,
) -> ObjectiveAssessmentIntent:
    value = item.get("assessment_intent")
    if isinstance(value, str) and value in ObjectiveAssessmentIntent:
        return ObjectiveAssessmentIntent(value)
    if not assessable:
        return ObjectiveAssessmentIntent.NONE
    if "exam" in assessment_method.lower():
        return ObjectiveAssessmentIntent.EXAM_PREP
    return ObjectiveAssessmentIntent.FORMATIVE


def _inference_reason(item: dict[str, str | bool]) -> str:
    missing = [key for key in ("importance", "assessable", "assessment_intent") if key not in item]
    if not missing:
        return "planner supplied objective strategy metadata"
    return "inferred missing fields: " + ", ".join(missing)


def _semantic_keys(result: ObjectiveNormalizationResult) -> tuple[str, ...]:
    return tuple(sorted(_semantic_key(item.description, item.bloom_level) for item in result.objectives))


def _semantic_key(description: str, bloom_level: str) -> str:
    words = " ".join(_WORD_RE.findall(description.lower()))
    return f"{bloom_level}:{words}"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
