"""Memory middleware — persists teacher identity across pipeline steps."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class MemoryMiddleware(BaseMiddleware):
    """Copies teacher_id from state into context metadata for downstream use."""

    name: str = "memory"
    order: int = 14

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        if state.get("teacher_id"):
            context.metadata["teacher_id"] = state["teacher_id"]
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state
