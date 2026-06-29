from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState


class ResearcherNodeState(TypedDict):
    lesson_plan: dict[str, Any]
    research_policy: str
    run_id: str
    current_step: int
    research_bundle: dict[str, Any] | None


class ResearcherState(MessagesState):
    """Internal state for the Researcher Agent.

    Graph node adapter extracts these fields from OhMyClassState before invocation,
    then injects research_bundle back into the graph state.
    """
    lesson_plan: dict[str, Any]
    research_policy: str
    run_id: str
    current_step: int
    research_bundle: dict[str, Any] | None
