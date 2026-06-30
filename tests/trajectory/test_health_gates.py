"""Health-gate tests for BudgetLedger / BudgetConfig.

``check_budget`` returns False when the budget is exhausted; it does not raise.
Callers are responsible for escalating when the return value is False.
All tests are deterministic — no LLM required.
"""
from __future__ import annotations

from services.gateway.budget import (
    BudgetConfig,
    BudgetLedger,
    check_budget,
    record_retry,
    record_usage,
)


# ---------------------------------------------------------------------------
# Token budget
# ---------------------------------------------------------------------------


class TestTokenBudget:
    def test_under_limit_returns_true(self):
        config = BudgetConfig(max_tokens_per_run=100)
        ledger = BudgetLedger(tokens_used=99)
        assert check_budget(ledger, config, "tokens") is True

    def test_at_limit_returns_false(self):
        """Exhausted: tokens_used == max_tokens_per_run → False."""
        config = BudgetConfig(max_tokens_per_run=100)
        ledger = BudgetLedger(tokens_used=100)
        assert check_budget(ledger, config, "tokens") is False

    def test_over_limit_returns_false(self):
        config = BudgetConfig(max_tokens_per_run=100)
        ledger = BudgetLedger(tokens_used=101)
        assert check_budget(ledger, config, "tokens") is False

    def test_zero_tokens_used_returns_true(self):
        config = BudgetConfig(max_tokens_per_run=100)
        ledger = BudgetLedger(tokens_used=0)
        assert check_budget(ledger, config, "tokens") is True

    def test_record_usage_increments_tokens(self):
        ledger = BudgetLedger()
        ledger = record_usage(ledger, "tokens", 50)
        assert ledger.tokens_used == 50


# ---------------------------------------------------------------------------
# Search budget
# ---------------------------------------------------------------------------


class TestSearchBudget:
    def test_under_limit_returns_true(self):
        config = BudgetConfig(max_searches_per_run=20)
        ledger = BudgetLedger(searches_used=19)
        assert check_budget(ledger, config, "searches") is True

    def test_at_limit_returns_false(self):
        config = BudgetConfig(max_searches_per_run=20)
        ledger = BudgetLedger(searches_used=20)
        assert check_budget(ledger, config, "searches") is False


# ---------------------------------------------------------------------------
# Fetch budget
# ---------------------------------------------------------------------------


class TestFetchBudget:
    def test_under_limit_returns_true(self):
        config = BudgetConfig(max_fetches_per_run=50)
        ledger = BudgetLedger(fetches_used=49)
        assert check_budget(ledger, config, "fetches") is True

    def test_at_limit_returns_false(self):
        config = BudgetConfig(max_fetches_per_run=50)
        ledger = BudgetLedger(fetches_used=50)
        assert check_budget(ledger, config, "fetches") is False


# ---------------------------------------------------------------------------
# Retry budget (per-artifact)
# ---------------------------------------------------------------------------


class TestRetryBudget:
    def test_empty_retry_dict_returns_true(self):
        """No retries consumed — budget is available."""
        config = BudgetConfig(max_retries_per_artifact=3)
        ledger = BudgetLedger(retries_used={})
        assert check_budget(ledger, config, "retries") is True

    def test_artifact_under_limit_returns_true(self):
        config = BudgetConfig(max_retries_per_artifact=3)
        ledger = BudgetLedger(retries_used={"artifact_1": 2})
        assert check_budget(ledger, config, "retries") is True

    def test_all_artifacts_exhausted_returns_false(self):
        """All tracked artifacts have hit/exceeded their limit → False."""
        config = BudgetConfig(max_retries_per_artifact=2)
        ledger = BudgetLedger(retries_used={"artifact_1": 3, "artifact_2": 2})
        assert check_budget(ledger, config, "retries") is False

    def test_one_artifact_under_limit_returns_true(self):
        """At least one artifact is still under limit → True."""
        config = BudgetConfig(max_retries_per_artifact=3)
        ledger = BudgetLedger(retries_used={"artifact_1": 3, "artifact_2": 1})
        assert check_budget(ledger, config, "retries") is True

    def test_record_retry_increments_counter(self):
        ledger = BudgetLedger()
        ledger = record_retry(ledger, "art-1")
        ledger = record_retry(ledger, "art-1")
        assert ledger.retries_used["art-1"] == 2

    def test_record_retry_starts_at_one(self):
        ledger = BudgetLedger()
        ledger = record_retry(ledger, "art-new")
        assert ledger.retries_used["art-new"] == 1


# ---------------------------------------------------------------------------
# Unknown check type
# ---------------------------------------------------------------------------


class TestUnknownBudgetCheck:
    def test_unknown_check_returns_false(self):
        """Unknown budget type — safe default is False (fail-closed)."""
        config = BudgetConfig()
        ledger = BudgetLedger()
        assert check_budget(ledger, config, "not_a_real_check") is False

    def test_parallel_artifacts_always_true(self):
        """parallel_artifacts is enforced at call-site, not ledger — always True."""
        config = BudgetConfig()
        ledger = BudgetLedger()
        assert check_budget(ledger, config, "parallel_artifacts") is True
