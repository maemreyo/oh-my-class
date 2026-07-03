from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState

from packages.agents.teaching_pack.stages import StageEnum


class UnitPlannerNodeState(TypedDict, total=False):
    raw_request: str
    class_info: dict[str, Any]
    grounding: dict[str, Any] | None
    persona_snapshot: dict[str, Any] | None
    run_id: str
    current_step: StageEnum
    lesson_sequence: dict[str, Any] | None
    template_prior: dict[str, Any] | None
    teacher_preferences: dict[str, Any] | None


class UnitPlannerState(MessagesState):
    raw_request: str
    class_info: dict[str, Any]
    grounding: dict[str, Any] | None
    persona_snapshot: dict[str, Any] | None
    run_id: str
    current_step: StageEnum
    lesson_sequence: dict[str, Any] | None
    template_prior: dict[str, Any] | None
    teacher_preferences: dict[str, Any] | None
