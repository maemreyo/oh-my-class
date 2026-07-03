"""Safety finish reason middleware — suppresses problematic finish reasons."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class SafetyFinishReasonMiddleware(BaseMiddleware):
    """Marks finish reasons that require special handling (length, content_filter)."""

    name: str = "safety_finish_reason"
    order: int = 9

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
        finish_reason = context.metadata.get("finish_reason")
        if finish_reason in ("length", "content_filter"):
            context.metadata["finish_reason_suppressed"] = True
        return state
