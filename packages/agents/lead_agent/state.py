from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph import MessagesState
from langgraph.managed.is_last_step import RemainingStepsManager


class LeadAgentState(MessagesState):
    """Internal state for the Lead Agent ReAct loop.

    Graph node adapter injects task and context before invocation, then
    reads result to update the graph state.

    recovery_guidance is written by D3 semantic recovery on failure — the
    next retry reads it to adjust its approach.
    """
    task: str
    context: dict[str, Any]
    result: dict[str, Any] | None
    recovery_guidance: str | None
    remaining_steps: Annotated[int, RemainingStepsManager]
