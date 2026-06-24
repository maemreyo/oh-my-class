"""Researcher Agent — compiled graph factory and main pipeline adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from packages.agents.state import OhMyClassState


def make_researcher_agent(checkpointer=None) -> "CompiledStateGraph":
    """Return a compiled LangGraph for the Researcher Agent.

    Can be run standalone:
        agent = make_researcher_agent()
        result = await agent.ainvoke({
            "messages": [], "lesson_plan": {...}, "research_policy": "standard",
            "run_id": "r1", "current_step": 7, "research_bundle": None,
        })
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.sub_agents.researcher.nodes import researcher_node
    from packages.agents.sub_agents.researcher.state import ResearcherState

    builder = StateGraph(ResearcherState)
    builder.add_node("researcher", researcher_node)
    builder.set_entry_point("researcher")
    builder.add_edge("researcher", END)
    return builder.compile(checkpointer=checkpointer)


async def researcher_graph_node(state: "OhMyClassState") -> dict[str, Any]:
    """Main pipeline graph node — adapter for the researcher compiled sub-graph."""
    from packages.agents.sub_agents.researcher.adapters import extract_researcher_state
    from packages.agents.sub_agents.researcher.nodes import researcher_node

    researcher_state = extract_researcher_state(state)
    return await researcher_node(researcher_state)
