from __future__ import annotations

from typing import Any

from langgraph.graph import MessagesState


class PlannerState(MessagesState):
    """Internal state for the Planner Agent.

    Graph node adapter extracts these fields from OhMyClassState before invocation,
    then injects lesson_plan back into the graph state.
    """
    raw_request: str
    class_info: dict[str, Any]
    run_id: str
    current_step: int
    lesson_plan: dict[str, Any] | None
