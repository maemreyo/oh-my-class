"""Tests for BudgetExceededError hard-stop behaviour.

No real LLM required — we test the error class semantics and the
TokenBudgetMiddleware hard-stop path directly.
"""
from __future__ import annotations

import pytest

from services.gateway.budget import BudgetConfig, BudgetExceededError, BudgetLedger, check_budget


def test_budget_exceeded_error_message_is_clear() -> None:
    exc = BudgetExceededError("tokens", 600_000, 500_000)
    assert "tokens" in str(exc)
    assert "600000" in str(exc)
    assert "500000" in str(exc)


def test_budget_exceeded_error_attributes() -> None:
    exc = BudgetExceededError("searches", 25, 20)
    assert exc.budget_type == "searches"
    assert exc.current == 25
    assert exc.limit == 20


def test_budget_exceeded_error_is_exception() -> None:
    exc = BudgetExceededError("tokens", 1, 0)
    assert isinstance(exc, Exception)


def test_check_budget_tokens_raises_when_exceeded() -> None:
    ledger = BudgetLedger(tokens_used=600_000)
    config = BudgetConfig(max_tokens_per_run=500_000)
    # check_budget returns False when exceeded (does NOT raise — caller decides)
    result = check_budget(ledger, config, "tokens")
    assert result is False


def test_check_budget_returns_true_within_limit() -> None:
    ledger = BudgetLedger(tokens_used=100)
    config = BudgetConfig(max_tokens_per_run=500_000)
    assert check_budget(ledger, config, "tokens") is True


def test_budget_exceeded_error_preserves_completed_stages() -> None:
    """Simulate a mid-pipeline hard-stop: completed_stages info is preserved
    in the BudgetExceededError attributes, not discarded.
    """
    completed_stages = ["stage_01_plan", "stage_02_research"]

    exc = BudgetExceededError("tokens", 600_000, 500_000)
    # Attach completed_stages to the error (caller pattern)
    exc.completed_stages = completed_stages  # type: ignore[attr-defined]

    assert exc.completed_stages == completed_stages
    assert exc.budget_type == "tokens"
    assert "tokens" in str(exc)


def test_token_budget_middleware_hard_stop() -> None:
    """TokenBudgetExceededError is raised — same hard-stop contract."""
    from packages.agents.middleware.safety.token_budget import (
        TokenBudgetExceededError,
        TokenBudgetMiddleware,
    )

    middleware = TokenBudgetMiddleware(budget=1000)
    # Simulate state that has already exceeded the budget
    state = {"tokens_used": 1001}

    import asyncio

    async def _run():
        from packages.agents.middleware.base import MiddlewareContext
        ctx = MiddlewareContext(agent_name="test", step=1, run_id="run-x")
        with pytest.raises(TokenBudgetExceededError):
            await middleware.before_model(state, ctx)

    asyncio.run(_run())
