"""System message coalescing middleware — marks system messages as coalesced."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class SystemMessageCoalescingMiddleware(BaseMiddleware):
    """Sets system_messages_coalesced flag in context metadata."""

    name: str = "system_message_coalescing"
    order: int = 22

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        context.metadata["system_messages_coalesced"] = True
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state
