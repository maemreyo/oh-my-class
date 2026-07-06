"""Canonical Teaching Pack stage names and event metadata."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, assert_never


class StageEnum(StrEnum):
    """Stable stage identifiers for Teaching Pack."""

    SETUP_CONTRACT = "setup_contract"
    TRIAGE = "triage"
    UNIT_PLANNING = "unit_planning"
    UNIT_APPROVAL = "unit_approval"
    UNIT_PREP = "unit_prep"
    PREPLANNING_SEARCH = "preplanning_search"
    PLANNING_BLUEPRINT = "planning_blueprint"
    PROVISIONAL_COMPONENT_STRATEGY = "provisional_component_strategy"
    POST_BLUEPRINT_RESEARCH = "post_blueprint_research"
    FINALIZE_COMPONENT_STRATEGY = "finalize_component_strategy"
    ARTIFACT_WORKFLOW = "artifact_workflow"
    RENDER_QUALITY = "render_quality"
    COMPLIANCE_GATE = "compliance_gate"
    TEACHER_APPROVAL = "teacher_approval"
    EXPORT_FINALIZE = "export_finalize"

    @property
    def started_event(self) -> str:
        """Return the canonical event name emitted when the stage starts."""
        return _event_name(self, "started")

    @property
    def completed_event(self) -> str:
        """Return the canonical event name emitted when the stage completes."""
        return _event_name(self, "completed")


TeachingPackStage = StageEnum


TEACHING_PACK_STAGES: Final[tuple[StageEnum, ...]] = (
    StageEnum.SETUP_CONTRACT,
    StageEnum.TRIAGE,
    StageEnum.PREPLANNING_SEARCH,
    StageEnum.PLANNING_BLUEPRINT,
    StageEnum.POST_BLUEPRINT_RESEARCH,
    StageEnum.ARTIFACT_WORKFLOW,
    StageEnum.RENDER_QUALITY,
    StageEnum.COMPLIANCE_GATE,
    StageEnum.TEACHER_APPROVAL,
    StageEnum.EXPORT_FINALIZE,
)

TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY: Final[tuple[StageEnum, ...]] = (
    StageEnum.SETUP_CONTRACT,
    StageEnum.TRIAGE,
    StageEnum.PREPLANNING_SEARCH,
    StageEnum.PLANNING_BLUEPRINT,
    StageEnum.PROVISIONAL_COMPONENT_STRATEGY,
    StageEnum.POST_BLUEPRINT_RESEARCH,
    StageEnum.FINALIZE_COMPONENT_STRATEGY,
    StageEnum.TEACHER_APPROVAL,
    StageEnum.ARTIFACT_WORKFLOW,
    StageEnum.RENDER_QUALITY,
    StageEnum.COMPLIANCE_GATE,
    StageEnum.EXPORT_FINALIZE,
)


def teaching_pack_stages(component_strategy_enabled: bool = False) -> tuple[StageEnum, ...]:
    if component_strategy_enabled:
        return TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY
    return TEACHING_PACK_STAGES


def stage_number(stage: StageEnum) -> int:
    for index, candidate in enumerate(TEACHING_PACK_STAGES, start=1):
        if candidate is stage:
            return index
    return len(TEACHING_PACK_STAGES) + 1


def _event_name(stage: StageEnum, suffix: str) -> str:
    match stage:
        case StageEnum.SETUP_CONTRACT:
            value = "setup_contract"
        case StageEnum.TRIAGE:
            value = "triage"
        case StageEnum.UNIT_PLANNING:
            value = "unit_planning"
        case StageEnum.UNIT_APPROVAL:
            value = "unit_approval"
        case StageEnum.UNIT_PREP:
            value = "unit_prep"
        case StageEnum.PREPLANNING_SEARCH:
            value = "preplanning_search"
        case StageEnum.PLANNING_BLUEPRINT:
            value = "planning_blueprint"
        case StageEnum.PROVISIONAL_COMPONENT_STRATEGY:
            value = "provisional_component_strategy"
        case StageEnum.POST_BLUEPRINT_RESEARCH:
            value = "post_blueprint_research"
        case StageEnum.FINALIZE_COMPONENT_STRATEGY:
            value = "finalize_component_strategy"
        case StageEnum.ARTIFACT_WORKFLOW:
            value = "artifact_workflow"
        case StageEnum.RENDER_QUALITY:
            value = "render_quality"
        case StageEnum.COMPLIANCE_GATE:
            value = "compliance_gate"
        case StageEnum.TEACHER_APPROVAL:
            value = "teacher_approval"
        case StageEnum.EXPORT_FINALIZE:
            value = "export_finalize"
        case unreachable:
            assert_never(unreachable)
    return f"teaching_pack.{value}.{suffix}"
