from __future__ import annotations

from langgraph.graph import MessagesState


class ReviewerState(MessagesState):
    """Internal state for the Reviewer Agent.

    Graph node adapter extracts these fields from OhMyClassState before invocation,
    then injects quality_scores and quality_passed back into the graph state.
    """
    artifacts: list[dict]
    lesson_plan: dict
    quality_scores: dict | None
    quality_passed: bool | None
