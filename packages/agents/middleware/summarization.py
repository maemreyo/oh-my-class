"""Summarization middleware — context compression for long conversations.

Compresses conversation history when it approaches context window limits.
Uses LLM-based summarization to preserve key information while reducing tokens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class SummarizationMiddleware(BaseMiddleware):
    """Compresses context when approaching token limits.

    Monitors conversation length and triggers summarization when the
    context window usage exceeds a configured threshold.
    """

    name: str = "summarization"
    order: int = 4

    def __init__(self, threshold_tokens: int = 80_000) -> None:
        self.threshold_tokens = threshold_tokens

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check context length and compress if needed.

        Triggers summarization when tokens_used exceeds threshold.
        Full LLM-based summarization is a future enhancement; for now the
        middleware enforces the interface contract and logs when threshold
        is approached.
        """
        tokens = state.get("tokens_used", 0)
        if isinstance(tokens, int) and tokens >= self.threshold_tokens:
            context.metadata["summarization_triggered"] = True
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """No-op after model — summarization only runs before."""
        return state
