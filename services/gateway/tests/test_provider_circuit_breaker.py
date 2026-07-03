"""Tests for the per-provider circuit breaker."""
from __future__ import annotations

import time

from packages.llm_client.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    breaker_for,
    should_skip_provider,
)


class SharedStore:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, float | int | str]] = {}

    def get(self, key: str) -> dict[str, float | int | str] | None:
        return self.values.get(key)

    def set(self, key: str, value: dict[str, float | int | str], _ttl_seconds: float) -> None:
        self.values[key] = value


def test_breaker_starts_closed() -> None:
    cb = CircuitBreaker()
    assert cb.state is CircuitState.CLOSED
    assert cb.is_open() is False


def test_breaker_opens_after_threshold_failures() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open() is False  # not yet
    cb.record_failure()
    assert cb.is_open() is True
    assert cb.state is CircuitState.OPEN


def test_breaker_does_not_open_before_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=5)
    for _ in range(4):
        cb.record_failure()
    assert cb.is_open() is False


def test_breaker_transitions_to_half_open_after_recovery() -> None:
    cb = CircuitBreaker(failure_threshold=2, recovery_seconds=0.05)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open() is True

    time.sleep(0.1)
    # is_open() triggers the OPEN → HALF_OPEN transition
    result = cb.is_open()
    assert result is False
    assert cb.state is CircuitState.HALF_OPEN


def test_record_success_in_half_open_closes_breaker() -> None:
    cb = CircuitBreaker(failure_threshold=2, recovery_seconds=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.1)
    cb.is_open()  # trigger HALF_OPEN transition
    assert cb.state is CircuitState.HALF_OPEN

    cb.record_success()
    assert cb.state is CircuitState.CLOSED
    assert cb.is_open() is False


def test_reset_clears_all_state() -> None:
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()
    assert cb.is_open() is True
    cb.reset()
    assert cb.state is CircuitState.CLOSED
    assert cb.is_open() is False


def test_record_success_from_closed_stays_closed() -> None:
    cb = CircuitBreaker()
    cb.record_success()
    assert cb.state is CircuitState.CLOSED


def test_global_breaker_for_returns_same_instance() -> None:
    from packages.llm_client.circuit_breaker import _breakers
    import packages.llm_client.circuit_breaker as breaker_module

    _breakers.clear()
    breaker_module._provider_store = None
    b1 = breaker_for("openai")
    b2 = breaker_for("openai")
    assert b1 is b2


def test_should_skip_provider_false_when_closed() -> None:
    from packages.llm_client.circuit_breaker import _breakers
    import packages.llm_client.circuit_breaker as breaker_module

    _breakers.clear()
    breaker_module._provider_store = None
    assert should_skip_provider("provider-x") is False


def test_should_skip_provider_true_after_failures() -> None:
    from packages.llm_client.circuit_breaker import _breakers
    import packages.llm_client.circuit_breaker as breaker_module

    _breakers.clear()
    breaker_module._provider_store = SharedStore()
    cb = breaker_for("flaky-provider")
    for _ in range(3):
        cb.record_failure()
    assert should_skip_provider("flaky-provider") is True
