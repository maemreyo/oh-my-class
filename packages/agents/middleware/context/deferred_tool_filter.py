"""Deferred tool filter middleware — marks tool filtering state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class DeferredToolFilterMiddleware(BaseMiddleware):
    """Initializes tools_filtered flag in context metadata."""

    name: str = "deferred_tool_filter"
    order: int = 21

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        context.metadata["tools_filtered"] = False
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state
