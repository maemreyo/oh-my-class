from __future__ import annotations

from typing import Any

from packages.agents.sub_agents.researcher.state import ResearcherState


def extract_researcher_state(graph_state: dict[str, Any]) -> ResearcherState:
    """Extract fields from OhMyClassState to build ResearcherState."""
    return ResearcherState(
        messages=[],
        lesson_plan=graph_state.get("lesson_plan") or {},
        research_policy=graph_state.get("research_policy", "standard"),
        run_id=graph_state.get("run_id", ""),
        current_step=graph_state.get("current_step", 7),
        research_bundle=None,
    )


def inject_researcher_result(researcher_state: ResearcherState) -> dict[str, Any]:
    """Map ResearcherState output back to graph state partial update."""
    return {"research_bundle": researcher_state.get("research_bundle")}
