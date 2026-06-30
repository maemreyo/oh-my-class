"""Canonical Teaching Pack stage names and event metadata."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, assert_never


class TeachingPackStage(StrEnum):
    """Stable stage identifiers for Teaching Pack."""

    SETUP_CONTRACT = "setup_contract"
    TRIAGE = "triage"
    PREPLANNING_SEARCH = "preplanning_search"
    PLANNING_BLUEPRINT = "planning_blueprint"
    POST_BLUEPRINT_RESEARCH = "post_blueprint_research"
    ARTIFACT_WORKFLOW = "artifact_workflow"
    RENDER_QUALITY = "render_quality"
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


TEACHING_PACK_STAGES: Final[tuple[TeachingPackStage, ...]] = (
    TeachingPackStage.SETUP_CONTRACT,
    TeachingPackStage.TRIAGE,
    TeachingPackStage.PREPLANNING_SEARCH,
    TeachingPackStage.PLANNING_BLUEPRINT,
    TeachingPackStage.POST_BLUEPRINT_RESEARCH,
    TeachingPackStage.ARTIFACT_WORKFLOW,
    TeachingPackStage.RENDER_QUALITY,
    TeachingPackStage.TEACHER_APPROVAL,
    TeachingPackStage.EXPORT_FINALIZE,
)


def _event_name(stage: TeachingPackStage, suffix: str) -> str:
    match stage:
        case TeachingPackStage.SETUP_CONTRACT:
            value = "setup_contract"
        case TeachingPackStage.TRIAGE:
            value = "triage"
        case TeachingPackStage.PREPLANNING_SEARCH:
            value = "preplanning_search"
        case TeachingPackStage.PLANNING_BLUEPRINT:
            value = "planning_blueprint"
        case TeachingPackStage.POST_BLUEPRINT_RESEARCH:
            value = "post_blueprint_research"
        case TeachingPackStage.ARTIFACT_WORKFLOW:
            value = "artifact_workflow"
        case TeachingPackStage.RENDER_QUALITY:
            value = "render_quality"
        case TeachingPackStage.TEACHER_APPROVAL:
            value = "teacher_approval"
        case TeachingPackStage.EXPORT_FINALIZE:
            value = "export_finalize"
        case unreachable:
            assert_never(unreachable)
    return f"teaching_pack.{value}.{suffix}"
