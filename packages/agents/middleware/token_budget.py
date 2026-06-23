"""Token budget middleware — per-run cost ceiling enforcement.

Tracks cumulative token usage and cost per pipeline run.
Blocks LLM calls when the budget is exceeded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TokenBudgetMiddleware(BaseMiddleware):
    """Enforces per-run token and cost ceilings.

    Reads tokens_used and cost_usd from state.
    Raises TokenBudgetExceeded when ceiling is hit.
    """

    name: str = "token_budget"
    order: int = 2

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check remaining budget before LLM call.

        TODO: Load budget limits from config, compare against state cost_usd.
        """
        # TODO: Load max_cost_usd and max_tokens from gate-config.yaml
        # TODO: If state["cost_usd"] >= max_cost_usd, raise TokenBudgetExceeded
        # TODO: If state["tokens_used"] >= max_tokens, raise TokenBudgetExceeded
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Update token/cost counters after LLM call.

        TODO: Parse usage metadata from LLM response, update state.
        """
        # TODO: Extract token counts from response metadata
        # TODO: Update state["tokens_used"] and state["cost_usd"]
        return state
