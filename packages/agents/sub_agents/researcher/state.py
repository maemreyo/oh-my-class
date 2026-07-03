from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState

from packages.agents.teaching_pack.stages import StageEnum


class ResearcherNodeState(TypedDict):
    lesson_plan: dict[str, Any]
    research_policy: str
    run_id: str
    current_step: StageEnum
    research_bundle: dict[str, Any] | None


class ResearcherState(MessagesState):
    lesson_plan: dict[str, Any]
    research_policy: str
    run_id: str
    current_step: StageEnum
    research_bundle: dict[str, Any] | None
