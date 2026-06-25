from __future__ import annotations

from typing import Any

from langgraph.graph import MessagesState


class ReviewerState(MessagesState):
    """Internal state for the Reviewer Agent.

    Graph node adapter extracts these fields from OhMyClassState before invocation,
    then injects quality_scores and quality_passed back into the graph state.
    """
    artifacts: list[dict[str, Any]]
    lesson_plan: dict[str, Any]
    quality_scores: dict[str, Any] | None
    quality_passed: bool | None
