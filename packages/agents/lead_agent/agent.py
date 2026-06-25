"""Lead Agent factory — B2 Tool Sequencer with Semantic Recovery.

The Lead Agent uses create_react_agent (B2 pattern):
- deterministic tool sequencing for the standard path
- LLM-driven recovery guidance on retry (D3 hybrid)
- system prompt loaded from prompts/system.md (G2)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import SecretStr

from packages.agents.lead_agent.prompts import load_system_prompt
from packages.agents.lead_agent.state import LeadAgentState
from packages.agents.lead_agent.tools import SUB_AGENT_TOOLS

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


def make_lead_agent(
    model: Any = None,
    checkpointer: Any = None,
    tools: list[Any] | None = None,
) -> CompiledStateGraph[Any, Any]:
    """Factory — returns a compiled ReAct graph for the Lead Agent.

    Routes through 9Router sidecar at NINEROUTER_BASE_URL (default: http://localhost:20128/v1).
    Model: gpt-5.4 → 9Router combo f.pro.

    Args:
        model: LangChain-compatible chat model. Defaults to ChatOpenAI via 9Router.
        checkpointer: LangGraph checkpointer. Defaults to MemorySaver.
        tools: Sub-agent tool list. Defaults to SUB_AGENT_TOOLS.

    Returns:
        Compiled ReAct graph ready for invocation.
    """
    import os

    llm = model or ChatOpenAI(
        model="gpt-5.4",
        base_url=os.environ.get("NINEROUTER_BASE_URL", "http://localhost:20128/v1"),
        api_key=SecretStr(os.environ.get("NINEROUTER_API_KEY", "no-key")),
        temperature=0,
    )
    system_prompt = load_system_prompt()

    return create_react_agent(
        model=llm,
        tools=tools if tools is not None else SUB_AGENT_TOOLS,
        state_schema=LeadAgentState,
        prompt=SystemMessage(content=system_prompt),
        checkpointer=checkpointer if checkpointer is not None else MemorySaver(),
    )
