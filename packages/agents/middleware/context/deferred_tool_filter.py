"""Deferred tool filter middleware — marks tool filtering state."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class DeferredToolFilterMiddleware(BaseMiddleware):
    """Initializes tools_filtered flag in context metadata."""

    name: str = "deferred_tool_filter"
    order: int = 21

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        context.metadata["tools_filtered"] = False
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state
