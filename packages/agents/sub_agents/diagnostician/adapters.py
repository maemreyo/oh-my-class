from __future__ import annotations

from typing import Any

from common.contracts.student_response import StudentResponse

from packages.agents.sub_agents.diagnostician.state import DiagnosticianState


def extract_diagnostician_state(graph_state: dict[str, Any]) -> DiagnosticianState:
    """Extract and validate fields from OhMyClassState to build DiagnosticianState.

    Validates student_responses against StudentResponse schema so downstream
    nodes receive clean, typed data instead of arbitrary dicts.
    """
    raw = graph_state.get("student_responses") or {}
    if raw:
        validated = StudentResponse.model_validate(raw)
        student_responses = validated.model_dump()
    else:
        student_responses = {}

    return DiagnosticianState(
        messages=[],
        student_responses=student_responses,
        run_id=graph_state.get("run_id", ""),
        current_step=graph_state.get("current_step", 0),
        diagnostic_report=None,
    )
