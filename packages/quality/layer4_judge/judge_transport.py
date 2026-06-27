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
    """Default LLM transport using litellm.acompletion."""
    import litellm

    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        extra_body=extra_body,
    )
    return response.choices[0].message.content
