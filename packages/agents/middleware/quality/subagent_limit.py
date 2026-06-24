"""Subagent limit middleware — enforces maximum active subagent count."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class SubagentLimitExceededError(Exception):
    """Raised when active subagent count exceeds the limit."""
    pass


class SubagentLimitMiddleware(BaseMiddleware):
    """Blocks LLM call when active_subagents >= 5."""

    name: str = "subagent_limit"
    order: int = 23

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        active = context.metadata.get("active_subagents", 0)
        if active >= 5:
            raise SubagentLimitExceededError(f"Too many active subagents: {active}")
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state
