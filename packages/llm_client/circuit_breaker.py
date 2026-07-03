from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import time

from packages.agents.healing.circuit_breaker import (
    BreakerStore,
    CircuitBreaker as LayeredCircuitBreaker,
)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: float = 60.0
    provider: str | None = None
    _failures: int = field(default=0, init=False, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)
    _delegate: LayeredCircuitBreaker | None = field(default=None, init=False, repr=False)

    @property
    def delegate(self) -> LayeredCircuitBreaker | None:
        if self.provider is None:
            return None
        if self._delegate is None:
            kwargs = {"store": _provider_store} if _provider_store is not None else {}
            self._delegate = LayeredCircuitBreaker.provider(
                self.provider,
                threshold=self.failure_threshold,
                recovery_timeout=self.recovery_seconds,
                **kwargs,
            )
        return self._delegate

    def record_success(self) -> None:
        if self.delegate is not None:
            self.delegate.record_success()
            return
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        if self.delegate is not None:
            self.delegate.record_failure()
            return
        self._failures += 1
        if self._state is CircuitState.CLOSED and self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def is_open(self) -> bool:
        if self.delegate is not None:
            return self.delegate.is_open()
        if self._state is CircuitState.CLOSED:
            return False
        if self._state is CircuitState.HALF_OPEN:
            return False
        if self._opened_at is not None and time.monotonic() - self._opened_at >= self.recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            return False
        return True

    def reset(self) -> None:
        self.record_success()

    @property
    def state(self) -> CircuitState:
        if self.delegate is not None:
            match self.delegate.state:
                case "open":
                    return CircuitState.OPEN
                case "half-open":
                    return CircuitState.HALF_OPEN
                case _:
                    return CircuitState.CLOSED
        return self._state


_breakers: dict[str, CircuitBreaker] = {}
_provider_store: BreakerStore | None = None


def breaker_for(provider: str) -> CircuitBreaker:
    if provider not in _breakers:
        _breakers[provider] = CircuitBreaker(provider=provider)
    return _breakers[provider]


def should_skip_provider(provider: str) -> bool:
    return breaker_for(provider).is_open()


def layered_provider_breaker(provider: str) -> LayeredCircuitBreaker:
    breaker = breaker_for(provider)
    delegate = breaker.delegate
    if delegate is None:
        raise RuntimeError("provider_breaker_unavailable")
    return delegate
