from __future__ import annotations

from langgraph.graph import MessagesState


class ContentCreatorState(MessagesState):
    """Internal state for the Content Creator Agent.

    Graph node adapter extracts these fields from OhMyClassState before invocation,
    then injects artifacts back into the graph state.
    """
    lesson_plan: dict
    research_bundle: dict
    artifact_types: list[str]
    theme: str
    run_id: str
    current_step: int
    artifacts: list[dict] | None
