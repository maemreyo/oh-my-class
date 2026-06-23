"""Token budget middleware — per-run cost ceiling enforcement.

Tracks cumulative token usage and cost per pipeline run.
Blocks LLM calls when the budget is exceeded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TokenBudgetExceededError(Exception):
    """Raised when token budget is exceeded."""
    pass


class TokenBudgetMiddleware(BaseMiddleware):
    """Enforces per-run token and cost ceilings.

    Reads tokens_used from state before each LLM call.
    Raises TokenBudgetExceededError when ceiling is hit.
    """

    name: str = "token_budget"
    order: int = 2

    def __init__(self, budget: int = 100_000) -> None:
        self.budget = budget
        self._used: int = 0

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check remaining budget before LLM call."""
        tokens = state.get("tokens_used", 0)
        if isinstance(tokens, int):
            self._used = tokens
        if self._used >= self.budget:
            raise TokenBudgetExceededError(
                f"Token budget exceeded: {self._used}/{self.budget}"
            )
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Sync token usage from state after LLM call."""
        tokens = state.get("tokens_used", 0)
        if isinstance(tokens, int):
            self._used = tokens
        return state
