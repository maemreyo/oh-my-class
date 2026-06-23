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
    order: int = 3

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check for and recover from dangling tool calls.

        TODO: Inspect conversation history for incomplete tool call sequences.
        """
        # TODO: Check for tool_calls with no matching tool_result
        # TODO: If found, append error recovery message to context
        # TODO: Reset any partial tool call state
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Record tool calls for tracking.

        TODO: Parse any tool calls from the response and register them.
        """
        # TODO: Extract tool call IDs from response
        # TODO: Register as pending until tool_result is received
        return state
