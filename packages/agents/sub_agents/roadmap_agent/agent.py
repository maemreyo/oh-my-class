"""Roadmap Agent — compiled graph factory and main pipeline adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from packages.agents.state import OhMyClassState


def make_roadmap_agent(checkpointer=None) -> CompiledStateGraph[Any, Any]:
    """Return a compiled LangGraph for the Roadmap Agent.

    For standalone use:
        agent = make_roadmap_agent()
        result = await agent.ainvoke({
            "messages": [], "diagnostic_report": {...},
            "student_profile": {...}, "run_id": "r1", "current_step": 0,
        })
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node
    from packages.agents.sub_agents.roadmap_agent.state import RoadmapAgentState

    builder = StateGraph(RoadmapAgentState)
    builder.add_node("roadmap", roadmap_node)
    builder.set_entry_point("roadmap")
    builder.add_edge("roadmap", END)
    return builder.compile(checkpointer=checkpointer)


async def roadmap_graph_node(state: OhMyClassState) -> dict[str, Any]:
    """Pipeline graph node for step_04b_roadmap.

    Skip policy:
    - diagnostic_report absent or empty → return {} (feature not requested)
    - diagnostic_report present but roadmap generation fails → ValueError propagates (fail closed)
    - RoadmapContent schema validation failure → ValidationError propagates (fail closed)
    """
    if not state.get("diagnostic_report"):
        return {}

    from packages.agents.sub_agents.roadmap_agent.adapters import extract_roadmap_agent_state
    from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

    roadmap_state = extract_roadmap_agent_state(state)  # type: ignore[arg-type]
    return await roadmap_node(roadmap_state)  # raises ValueError on LLM/schema error
