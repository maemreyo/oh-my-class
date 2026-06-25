from __future__ import annotations

from typing import NotRequired

from langgraph.graph import MessagesState


class RoadmapAgentState(MessagesState):
    """Internal state for the Roadmap Agent."""

    diagnostic_report: dict
    student_profile: NotRequired[dict | None]
    run_id: str
    current_step: int
    roadmap_artifact: NotRequired[dict | None]
