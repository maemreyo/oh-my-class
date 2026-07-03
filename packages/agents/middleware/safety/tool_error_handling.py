"""Tool error handling middleware — captures and marks tool-level errors."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class ToolErrorHandlingMiddleware(BaseMiddleware):
    """Marks tool_error_handled in context metadata when a tool error is present."""

    name: str = "tool_error_handling"
    order: int = 10

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        if context.metadata.get("tool_error"):
            context.metadata["tool_error_handled"] = True
        return state
