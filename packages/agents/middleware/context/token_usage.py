"""Token usage middleware — tracks per-step token deltas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TokenUsageMiddleware(BaseMiddleware):
    """Records step_start_tokens and computes step_token_delta after the LLM call."""

    name: str = "token_usage"
    order: int = 17

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        context.metadata["step_start_tokens"] = state.get("tokens_used", 0)
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        start = context.metadata.get("step_start_tokens", 0)
        current = state.get("tokens_used", 0)
        context.metadata["step_token_delta"] = current - start
        return state
