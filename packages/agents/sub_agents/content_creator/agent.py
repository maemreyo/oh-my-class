"""Content Creator Agent — compiled graph factory and main pipeline adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from packages.agents.state import OhMyClassState


def make_content_creator_agent(checkpointer=None) -> CompiledStateGraph[Any, Any]:
    """Return a compiled LangGraph for the Content Creator Agent.

    Can be run standalone:
        agent = make_content_creator_agent()
        result = await agent.ainvoke({
            "messages": [], "lesson_plan": {...}, "research_bundle": {...},
            "artifact_types": ["lesson"], "theme": "default",
            "run_id": "r1", "current_step": 8, "artifacts": None,
        })
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.sub_agents.content_creator.nodes import content_creator_node
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState

    builder = StateGraph(ContentCreatorState)
    builder.add_node("content_creator", content_creator_node)
    builder.set_entry_point("content_creator")
    builder.add_edge("content_creator", END)
    return builder.compile(checkpointer=checkpointer)


async def content_creator_graph_node(state: OhMyClassState) -> dict[str, Any]:
    """Main pipeline graph node — adapter for the content creator compiled sub-graph."""
    from packages.agents.sub_agents.content_creator.adapters import extract_content_creator_state
    from packages.agents.sub_agents.content_creator.nodes import content_creator_node

    cc_state = extract_content_creator_state(state)  # type: ignore[arg-type]
    return await content_creator_node(cc_state)
