"""Token usage middleware — tracks per-step token deltas."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class TokenUsageMiddleware(BaseMiddleware):
    """Records step_start_tokens and computes step_token_delta after the LLM call."""

    name: str = "token_usage"
    order: int = 12

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        context.metadata["step_start_tokens"] = state.get("tokens_used", 0)
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        start = context.metadata.get("step_start_tokens", 0)
        current = state.get("tokens_used", 0)
        context.metadata["step_token_delta"] = current - start
        return state
