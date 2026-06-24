"""Tool error handling middleware — captures and marks tool-level errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class ToolErrorHandlingMiddleware(BaseMiddleware):
    """Marks tool_error_handled in context metadata when a tool error is present."""

    name: str = "tool_error_handling"
    order: int = 10

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        if context.metadata.get("tool_error"):
            context.metadata["tool_error_handled"] = True
        return state
