"""Diagnostician Agent — compiled graph factory and main pipeline adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from packages.agents.state import OhMyClassState


def make_diagnostician_agent(checkpointer=None) -> CompiledStateGraph[Any, Any]:
    """Return a compiled LangGraph for the Diagnostician Agent.

    For standalone use:
        agent = make_diagnostician_agent()
        result = await agent.ainvoke({
            "messages": [], "student_responses": {...},
            "run_id": "r1", "current_step": 0,
        })
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node
    from packages.agents.sub_agents.diagnostician.state import DiagnosticianState

    builder = StateGraph(DiagnosticianState)
    builder.add_node("diagnostician", diagnostician_node)
    builder.set_entry_point("diagnostician")
    builder.add_edge("diagnostician", END)
    return builder.compile(checkpointer=checkpointer)


async def diagnostician_graph_node(state: OhMyClassState) -> dict[str, Any]:
    """Pipeline graph node for step_00_diagnostic.

    Skip policy:
    - student_responses absent or empty → return {} (feature not requested)
    - student_responses present but invalid → ValidationError propagates (fail closed)
    - LLM or schema failure → ValueError propagates (fail closed)
    """
    if not state.get("student_responses"):
        return {}

    from packages.agents.sub_agents.diagnostician.adapters import extract_diagnostician_state
    from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

    diagnostician_state = extract_diagnostician_state(state)  # type: ignore[arg-type]  # raises ValidationError on bad input
    return await diagnostician_node(diagnostician_state)       # raises ValueError on LLM/schema error  # noqa: E501
