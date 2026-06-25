from __future__ import annotations

from typing import Any

from packages.agents.sub_agents.roadmap_agent.state import RoadmapAgentState


def extract_roadmap_agent_state(graph_state: dict[str, Any]) -> RoadmapAgentState:
    """Extract fields from OhMyClassState to build RoadmapAgentState."""
    return RoadmapAgentState(
        messages=[],
        diagnostic_report=graph_state.get("diagnostic_report") or {},
        student_profile=graph_state.get("student_profile"),
        run_id=graph_state.get("run_id", ""),
        current_step=graph_state.get("current_step", 0),
        roadmap_artifact=None,
    )
