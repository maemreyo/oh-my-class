from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from langgraph.graph import MessagesState

from packages.agents.teaching_pack.stages import StageEnum


class ContentCreatorNodeState(TypedDict):
    lesson_plan: dict[str, Any]
    research_bundle: dict[str, Any]
    artifact_types: list[str]
    theme: str
    run_id: str
    current_step: StageEnum
    artifacts: list[dict[str, Any]] | None
    revision_feedback: NotRequired[str]
    use_hierarchical_creator: NotRequired[bool]
    force_section_failures: NotRequired[list[str]]
    disable_methodology_components: NotRequired[bool]
    component_effectiveness: NotRequired[dict[str, Any]]
    component_strategy_plan: NotRequired[dict[str, Any]]
    structure_preset: NotRequired[str | None]


class ContentCreatorState(MessagesState):
    lesson_plan: dict[str, Any]
    research_bundle: dict[str, Any]
    artifact_types: list[str]
    theme: str
    run_id: str
    current_step: StageEnum
    artifacts: list[dict[str, Any]] | None
