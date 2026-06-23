"""Lead Agent — factory function and node implementation.

The Lead Agent orchestrates the entire pipeline. It decomposes the teacher's
request into subtasks, delegates to sub-agents via task(), and synthesizes
results. It never generates educational content directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


# The Lead Agent uses gpt-5.4 via 9Router combo: f.pro
# (NOT direct OpenAI API — all traffic routes through 9Router sidecar)
def make_lead_agent(
    *,
    model: str | None = None,
    tools: list[str] | None = None,
) -> Any:
    """Create and configure the Lead Agent.

    The Lead Agent uses gpt-5.4 via LiteLLM → 9Router combo f.pro.
    Access to:
    - task: delegate to sub-agents
    - ask_clarification: request clarification from teacher
    - read_file: read workspace files
    - write_file: write workspace files

    Args:
        model: Override the configured model (default: from LEAD_AGENT_CONFIG).
        tools: Override the tool list (default: from LEAD_AGENT_CONFIG).

    Returns:
        Compiled LangGraph agent ready for invocation.
    """
    # TODO: Implement with langgraph prebuilt.create_react_agent or custom graph
    # config = LEAD_AGENT_CONFIG
    # resolved_model = model or config["model"]
    # resolved_tools = tools or config["tools"]
    # return create_react_agent(model=resolved_model, tools=resolved_tools, ...)
    raise NotImplementedError("make_lead_agent() stub — implement with LangGraph")


async def lead_agent_node(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node function for the Lead Agent.

    Reads the current pipeline state, determines the next action,
    and returns the state update.

    Args:
        state: Current pipeline state.

    Returns:
        Partial state update dict.
    """
    # TODO: Implement step routing logic based on state["current_step"]
    # TODO: Delegate to sub-agents via task() — never generate content directly
    # TODO: Return partial state update
    raise NotImplementedError("lead_agent_node() stub — implement pipeline routing")
