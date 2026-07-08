"""LLM transport protocol and default implementation for the judge.

Provides the injectable transport callable used by AdaptiveJudge,
enabling dependency inversion for testability.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

# ---------------------------------------------------------------------------
# LLM transport protocol — callable matching the async LLM interface.
# ---------------------------------------------------------------------------

LLMTransport = Callable[..., Coroutine[Any, Any, str]]


async def default_litellm_transport(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    extra_body: dict[str, Any],
) -> str:
    """Default LLM transport — routes through LLMClient, never bare litellm.

    Callers that need custom tagging/attribution (e.g. reviewer_node's
    AgentRuntime-backed transport) should keep injecting their own
    llm_transport; this default exists so *not* injecting one is still safe
    (governed by the same circuit breaker/middleware/observability as every
    other agent call) instead of silently bypassing all of it.
    """
    from packages.llm_client.client import ChatMessage, LLMClient

    tags = extra_body.get("metadata", {}).get("tags", []) if extra_body else []
    agent = next((t.split(":", 1)[1] for t in tags if t.startswith("agent:")), "layer4_judge")
    task = next((t.split(":", 1)[1] for t in tags if t.startswith(("metric:", "judge:"))), "llm_judge")

    client = LLMClient()
    response = await client.chat(
        model=model,
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in messages],
        agent=agent,
        task=task,
        temperature=temperature,
    )
    return response.content
