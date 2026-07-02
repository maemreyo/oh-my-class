from __future__ import annotations

from typing import Any

from langgraph.graph import MessagesState


class RoadmapAgentState(MessagesState):
    """Internal state for the Roadmap Agent."""

    diagnostic_report: dict[str, Any]
    student_profile: dict[str, Any] | None
    run_id: str
    current_step: int
    roadmap_artifact: dict[str, Any] | None
    use_structured_roadmap: bool | None
    kt_mastery: dict[str, Any] | None
