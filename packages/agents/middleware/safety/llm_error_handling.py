"""LLM error handling middleware — captures and marks LLM-level errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class LLMErrorHandlingMiddleware(BaseMiddleware):
    """Marks error state in context metadata when the LLM returns an error."""

    name: str = "llm_error_handling"
    order: int = 7

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
        if state.get("error"):
            context.metadata["llm_error_handled"] = True
        return state
