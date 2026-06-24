from __future__ import annotations

from typing import Any

from packages.agents.sub_agents.planner.state import PlannerState


def extract_planner_state(graph_state: dict[str, Any]) -> PlannerState:
    """Extract fields from OhMyClassState to build PlannerState."""
    return PlannerState(
        messages=[],
        raw_request=graph_state["raw_request"],
        class_info=graph_state.get("class_info", {}),
        run_id=graph_state.get("run_id", ""),
        current_step=graph_state.get("current_step", 3),
        lesson_plan=None,
    )


def inject_planner_result(planner_state: PlannerState) -> dict[str, Any]:
    """Map PlannerState output back to graph state partial update."""
    return {"lesson_plan": planner_state.get("lesson_plan")}
