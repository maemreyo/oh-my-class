"""Backward-compatibility shim — re-exports from safety tier.

The canonical location is packages.agents.middleware.safety.token_budget.
"""

from packages.agents.middleware.safety.token_budget import TokenBudgetExceededError, TokenBudgetMiddleware

__all__ = ["TokenBudgetExceededError", "TokenBudgetMiddleware"]
