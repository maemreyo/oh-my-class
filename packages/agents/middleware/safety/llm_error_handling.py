"""LLM error handling middleware — captures and marks LLM-level errors."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class LLMErrorHandlingMiddleware(BaseMiddleware):
    """Marks error state in context metadata when the LLM returns an error."""

    name: str = "llm_error_handling"
    order: int = 6

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
        if state.get("error"):
            context.metadata["llm_error_handled"] = True
        return state
