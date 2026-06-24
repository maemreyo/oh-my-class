"""Memory middleware — persists teacher identity across pipeline steps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class MemoryMiddleware(BaseMiddleware):
    """Copies teacher_id from state into context metadata for downstream use."""

    name: str = "memory"
    order: int = 19

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        if state.get("teacher_id"):
            context.metadata["teacher_id"] = state["teacher_id"]
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state
