from __future__ import annotations

from typing import Any

from packages.agents.sub_agents.reviewer.state import ReviewerState


def extract_reviewer_state(graph_state: dict[str, Any]) -> ReviewerState:
    """Extract fields from OhMyClassState to build ReviewerState."""
    return ReviewerState(
        messages=[],
        artifacts=graph_state.get("artifacts") or [],
        lesson_plan=graph_state.get("lesson_plan") or {},
        quality_scores=None,
        quality_passed=None,
    )


def inject_reviewer_result(reviewer_state: ReviewerState) -> dict[str, Any]:
    """Map ReviewerState output back to graph state partial update."""
    return {
        "quality_scores": reviewer_state.get("quality_scores"),
        "quality_passed": reviewer_state.get("quality_passed") or False,
    }
