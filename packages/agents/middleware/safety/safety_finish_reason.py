"""Safety finish reason middleware — suppresses problematic finish reasons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class SafetyFinishReasonMiddleware(BaseMiddleware):
    """Marks finish reasons that require special handling (length, content_filter)."""

    name: str = "safety_finish_reason"
    order: int = 12

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
        finish_reason = context.metadata.get("finish_reason")
        if finish_reason in ("length", "content_filter"):
            context.metadata["finish_reason_suppressed"] = True
        return state
