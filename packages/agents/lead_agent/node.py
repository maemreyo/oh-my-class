"""Lead Agent graph node — bridges OhMyClassState ↔ LeadAgentState.

D3 hybrid: graph handles structural retry limits; this node injects semantic
recovery guidance when revision_count > 0 and review results are available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

from packages.agents.lead_agent.recovery import build_recovery_context

_lead_agent = None


async def lead_agent_node(state: "OhMyClassState") -> dict[str, Any]:
    """LangGraph node — invokes the Lead Agent and writes results back to graph state.

    Extracts relevant context from OhMyClassState, builds the Lead Agent input,
    invokes the agent, and returns a partial state update.
    """
    global _lead_agent
    if _lead_agent is None:
        from packages.agents.lead_agent.agent import make_lead_agent
        _lead_agent = make_lead_agent()

    task = f"Create lesson materials for: {state['raw_request']}"
    context: dict[str, Any] = {
        "class_info": state.get("class_info", {}),
        "lesson_plan": state.get("lesson_plan"),
        "research_bundle": state.get("research_bundle"),
        "artifacts": state.get("artifacts", []),
        "revision_count": state.get("revision_count", 0),
    }

    messages: list[dict[str, Any]] = [{"role": "user", "content": task}]

    # D3: inject semantic recovery guidance on retry
    if state.get("review_results") and state.get("revision_count", 0) > 0:
        recovery_ctx = build_recovery_context(
            state["review_results"],
            state["revision_count"],
        )
        messages.insert(0, {"role": "system", "content": recovery_ctx})

    agent_input: dict[str, Any] = {
        "messages": messages,
        "task": task,
        "context": context,
        "result": None,
        "recovery_guidance": None,
    }

    result = _lead_agent.invoke(agent_input)

    updates: dict[str, Any] = {}
    if result.get("lesson_plan"):
        updates["lesson_plan"] = result["lesson_plan"]
    if result.get("research_bundle"):
        updates["research_bundle"] = result["research_bundle"]
    if result.get("artifacts"):
        updates["artifacts"] = result["artifacts"]
    if result.get("review_results"):
        updates["review_results"] = result["review_results"]

    return updates
