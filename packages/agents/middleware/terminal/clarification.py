"""Clarification middleware — last-in-chain gate for ambiguous requests.

INVARIANT-08: This middleware MUST always be last (order=30).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class ClarificationMiddleware(BaseMiddleware):
    """Flags when clarification is needed before proceeding.

    INVARIANT-08: Clarification middleware is always the last in the chain (order=30).
    """

    name: str = "clarification"
    order: int = 30

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        if state.get("clarification_needed"):
            context.metadata["clarification_requested"] = True
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state
