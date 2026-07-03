"""System message coalescing middleware — marks system messages as coalesced."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class SystemMessageCoalescingMiddleware(BaseMiddleware):
    """Sets system_messages_coalesced flag in context metadata."""

    name: str = "system_message_coalescing"
    order: int = 15

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        context.metadata["system_messages_coalesced"] = True
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state
