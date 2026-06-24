"""Planner Agent — compiled graph factory and main pipeline adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from packages.agents.state import OhMyClassState


def make_planner_agent(checkpointer=None) -> "CompiledStateGraph":
    """Return a compiled LangGraph for the Planner Agent.

    Can be run standalone:
        agent = make_planner_agent()
        result = await agent.ainvoke({
            "messages": [], "raw_request": "...", "class_info": {...},
            "run_id": "r1", "current_step": 3, "lesson_plan": None,
        })
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.sub_agents.planner.nodes import planner_node
    from packages.agents.sub_agents.planner.state import PlannerState

    builder = StateGraph(PlannerState)
    builder.add_node("planner", planner_node)
    builder.set_entry_point("planner")
    builder.add_edge("planner", END)
    return builder.compile(checkpointer=checkpointer)


async def planner_graph_node(state: "OhMyClassState") -> dict[str, Any]:
    """Main pipeline graph node — adapter for the planner compiled sub-graph."""
    from packages.agents.sub_agents.planner.adapters import extract_planner_state
    from packages.agents.sub_agents.planner.nodes import planner_node

    planner_state = extract_planner_state(state)
    return await planner_node(planner_state)
