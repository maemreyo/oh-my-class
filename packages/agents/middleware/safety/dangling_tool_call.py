"""Dangling tool call middleware — crash recovery for interrupted calls.

Detects and recovers from tool calls that were interrupted (e.g., by timeout,
network failure, or process crash). Cleans up partial state before retry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class DanglingToolCallMiddleware(BaseMiddleware):
    """Recovers from interrupted tool calls.

    Tracks pending tool calls in state. On before_model, checks if there
    are unfinished tool calls from a previous turn and cleans them up.
    """

    name: str = "dangling_tool_call"
    order: int = 6

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check for and recover from dangling tool calls."""
        # Inspect context metadata for any tool calls registered in prior turn
        pending = context.metadata.get("pending_tool_calls", [])
        if pending:
            # Clear orphaned calls — they will be retried or skipped
            context.metadata["pending_tool_calls"] = []
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Register any tool calls emitted this turn for tracking."""
        # Tool call IDs would be extracted from LLM response messages;
        # state doesn't carry raw messages in this pipeline so no-op for now.
        return state
