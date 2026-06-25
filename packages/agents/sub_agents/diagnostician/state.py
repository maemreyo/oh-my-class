from __future__ import annotations

from typing import Any

from langgraph.graph import MessagesState


class DiagnosticianState(MessagesState):
    """Internal state for the Diagnostician Agent."""

    student_responses: dict[str, Any]
    run_id: str
    current_step: int
    diagnostic_report: dict[str, Any] | None
