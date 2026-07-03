from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState

from packages.agents.teaching_pack.stages import StageEnum


class DiagnosticianState(MessagesState):
    """Internal state for the Diagnostician Agent."""

    student_responses: dict[str, Any]
    run_id: str
    current_step: StageEnum
    diagnostic_report: dict[str, Any] | None
    use_structured_diagnostic: bool | None


class DiagnosticianNodeState(TypedDict, total=False):
    student_responses: dict[str, Any]
    run_id: str
    current_step: StageEnum
    diagnostic_report: dict[str, Any] | None
    use_structured_diagnostic: bool
