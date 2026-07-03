from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState

from packages.agents.teaching_pack.stages import StageEnum


class PlannerNodeState(TypedDict, total=False):
    raw_request: str
    class_info: dict[str, Any]
    run_id: str
    current_step: StageEnum
    lesson_plan: dict[str, Any] | None
    seed: dict[str, Any] | None
    use_staged_planner: bool
    persona_snapshot: dict[str, Any] | None
    class_knowledge_graph: dict[str, Any] | None
    kt_mastery: dict[str, Any] | None
    teacher_preferences: dict[str, Any] | None


class PlannerState(MessagesState):
    raw_request: str
    class_info: dict[str, Any]
    run_id: str
    current_step: StageEnum
    lesson_plan: dict[str, Any] | None
    seed: dict[str, Any] | None
    use_staged_planner: bool
    persona_snapshot: dict[str, Any] | None
    class_knowledge_graph: dict[str, Any] | None
    kt_mastery: dict[str, Any] | None
    teacher_preferences: dict[str, Any] | None
