"""Per-run budget tracking for Pipeline V2.

Pure in-memory dataclasses — no DB persistence.  Each pipeline run creates
a ``BudgetLedger`` bounded by a ``BudgetConfig``.  Agents record usage via
``record_usage`` and check limits via ``check_budget`` before expensive
operations (LLM calls, web searches, fetches, retries).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceededError(Exception):
    """Raised when a budget check fails and callers need structured context."""

    def __init__(self, budget_type: str, current: int, limit: int) -> None:
        self.budget_type = budget_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Budget exceeded for {budget_type}: {current} >= {limit}",
        )


@dataclass
class BudgetConfig:
    """Configurable limits for a single pipeline run."""

    max_tokens_per_run: int = 500_000
    max_searches_per_run: int = 20
    max_fetches_per_run: int = 50
    max_retries_per_artifact: int = 3
    max_parallel_artifacts: int = 3


@dataclass
class BudgetLedger:
    """Mutable counters tracking resource consumption for a run."""

    tokens_used: int = 0
    searches_used: int = 0
    fetches_used: int = 0
    retries_used: dict[str, int] = field(default_factory=dict)


def check_budget(
    ledger: BudgetLedger,
    config: BudgetConfig,
    check: str,
) -> bool:
    """Return ``True`` if *ledger* is still under the limit for *check*.

    Supported *check* values: ``"tokens"``, ``"searches"``, ``"fetches"``,
    ``"retries"`` (aggregated), ``"parallel_artifacts"`` (always True —
    enforced at the caller site via ``max_parallel_artifacts``).
    """
    match check:
        case "tokens":
            return ledger.tokens_used < config.max_tokens_per_run
        case "searches":
            return ledger.searches_used < config.max_searches_per_run
        case "fetches":
            return ledger.fetches_used < config.max_fetches_per_run
        case "retries":
            return any(
                count < config.max_retries_per_artifact
                for count in ledger.retries_used.values()
            ) or not ledger.retries_used
        case "parallel_artifacts":
            return True  # enforced at the caller, not the ledger
        case _:
            return False


def record_usage(
    ledger: BudgetLedger,
    check: str,
    amount: int = 1,
) -> BudgetLedger:
    """Increment the relevant counter and return the updated ledger.

    For ``"retries"`` pass ``artifact_id`` as the first positional arg
    via ``record_retry(ledger, artifact_id)`` — handled by the dedicated
    helper below.
    """
    match check:
        case "tokens":
            ledger.tokens_used += amount
        case "searches":
            ledger.searches_used += amount
        case "fetches":
            ledger.fetches_used += amount
    return ledger


def record_retry(ledger: BudgetLedger, artifact_id: str) -> BudgetLedger:
    """Increment the retry counter for a specific artifact."""
    ledger.retries_used[artifact_id] = ledger.retries_used.get(artifact_id, 0) + 1
    return ledger
