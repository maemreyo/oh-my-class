"""Canonical Pipeline V2 stage names and event metadata."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, assert_never


class PipelineV2Stage(StrEnum):
    """Stable stage identifiers for Pipeline V2."""

    SETUP_CONTRACT = "setup_contract"
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


PIPELINE_V2_STAGES: Final[tuple[PipelineV2Stage, ...]] = (
    PipelineV2Stage.SETUP_CONTRACT,
    PipelineV2Stage.PREPLANNING_SEARCH,
    PipelineV2Stage.PLANNING_BLUEPRINT,
    PipelineV2Stage.POST_BLUEPRINT_RESEARCH,
    PipelineV2Stage.ARTIFACT_WORKFLOW,
    PipelineV2Stage.RENDER_QUALITY,
    PipelineV2Stage.TEACHER_APPROVAL,
    PipelineV2Stage.EXPORT_FINALIZE,
)


def _event_name(stage: PipelineV2Stage, suffix: str) -> str:
    match stage:
        case PipelineV2Stage.SETUP_CONTRACT:
            value = "setup_contract"
        case PipelineV2Stage.PREPLANNING_SEARCH:
            value = "preplanning_search"
        case PipelineV2Stage.PLANNING_BLUEPRINT:
            value = "planning_blueprint"
        case PipelineV2Stage.POST_BLUEPRINT_RESEARCH:
            value = "post_blueprint_research"
        case PipelineV2Stage.ARTIFACT_WORKFLOW:
            value = "artifact_workflow"
        case PipelineV2Stage.RENDER_QUALITY:
            value = "render_quality"
        case PipelineV2Stage.TEACHER_APPROVAL:
            value = "teacher_approval"
        case PipelineV2Stage.EXPORT_FINALIZE:
            value = "export_finalize"
        case unreachable:
            assert_never(unreachable)
    return f"pipeline_v2.{value}.{suffix}"
