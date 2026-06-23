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

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check context length and compress if needed.

        TODO: Estimate current token count of conversation history.
        TODO: If exceeds threshold, summarize older messages.
        """
        # TODO: Count tokens in conversation history
        # TODO: If > threshold (e.g. 80% of context window), trigger summarization
        # TODO: Replace old messages with summary
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """No-op after model — summarization only runs before."""
        return state
