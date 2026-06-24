from __future__ import annotations

from typing import Any

from packages.agents.sub_agents.content_creator.state import ContentCreatorState


def extract_content_creator_state(graph_state: dict[str, Any]) -> ContentCreatorState:
    """Extract fields from OhMyClassState to build ContentCreatorState."""
    return ContentCreatorState(
        messages=[],
        lesson_plan=graph_state.get("lesson_plan") or {},
        research_bundle=graph_state.get("research_bundle") or {},
        artifact_types=graph_state.get("artifact_types") or ["lesson"],
        theme=graph_state.get("theme", "default"),
        run_id=graph_state.get("run_id", ""),
        current_step=graph_state.get("current_step", 8),
        artifacts=None,
    )


def inject_content_creator_result(cc_state: ContentCreatorState) -> dict[str, Any]:
    """Map ContentCreatorState output back to graph state partial update."""
    return {"artifacts": cc_state.get("artifacts") or []}
