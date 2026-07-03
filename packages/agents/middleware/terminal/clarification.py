"""Clarification middleware — last-in-chain gate for ambiguous requests.

INVARIANT-08: This middleware MUST always be last (order=23).
"""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class ClarificationMiddleware(BaseMiddleware):
    """Flags when clarification is needed before proceeding.

    INVARIANT-08: Clarification middleware is always the last in the chain (order=23).
    """

    name: str = "clarification"
    order: int = 23

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        if state.get("clarification_needed"):
            context.metadata["clarification_requested"] = True
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        _ = context
        return state
