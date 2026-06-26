from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import SecretStr

from packages.agents.config.models import LLM, MODELS
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
    llm = model or ChatOpenAI(
        model=MODELS.lead_agent,
        base_url=LLM.base_url,
        api_key=SecretStr(LLM.api_key or "no-key"),
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
