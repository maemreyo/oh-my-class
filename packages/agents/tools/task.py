"""Task delegation tool — stub implementation.

The primary mechanism for the Lead Agent to delegate work to sub-agents.
The Lead Agent NEVER calls an LLM directly — it always delegates via task().

INVARIANT-01: Lead Agent NEVER generates content directly via LLM.
It only calls task(agent_name, prompt).
"""

from __future__ import annotations

from typing import Any


async def task(
    agent_name: str,
    prompt: str,
    *,
    context: dict[str, Any] | None = None,
    max_turns: int | None = None,
    model_override: str | None = None,
) -> dict[str, Any]:
    """Delegate a task to a named sub-agent.

    Args:
        agent_name: Target agent — one of 'planner', 'researcher',
            'content_creator', 'reviewer'.
        prompt: Task description / instruction for the sub-agent.
        context: Optional additional context from the pipeline state.
        max_turns: Override the agent's default max_turns.
        model_override: Override the agent's configured model.

    Returns:
        Agent response as a dict matching the agent's output schema.

    Raises:
        ValueError: If agent_name is not a recognized agent.
    """
    # TODO: Implement via LangGraph task delegation
    # Should invoke the named agent's compiled graph with the prompt
    raise NotImplementedError("task() stub — implement with LangGraph agent invocation")
