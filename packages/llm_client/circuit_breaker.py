"""Per-provider circuit breaker.

Tracks consecutive failures per provider. When the failure threshold is
reached the breaker opens (caller should skip that provider). After
recovery_seconds it moves to HALF_OPEN to probe recovery; a single success
closes it again.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: float = 60.0

    _failures: int = field(default=0, init=False, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)

    def record_success(self) -> None:
        """Reset on success; HALF_OPEN → CLOSED."""
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        """Accumulate failure; trip breaker when threshold is reached."""
        self._failures += 1
        if self._state is CircuitState.CLOSED and self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def is_open(self) -> bool:
        """Return True when the caller should NOT attempt the provider.

        Automatically transitions OPEN → HALF_OPEN after recovery_seconds.
        """
        if self._state is CircuitState.CLOSED:
            return False
        if self._state is CircuitState.HALF_OPEN:
            return False
        # OPEN — check if recovery window has elapsed
        if self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_seconds:
                self._state = CircuitState.HALF_OPEN
                return False
        return True

    def reset(self) -> None:
        """Force the breaker to CLOSED state."""
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    @property
    def state(self) -> CircuitState:
        return self._state


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

_breakers: dict[str, CircuitBreaker] = {}


def breaker_for(provider: str) -> CircuitBreaker:
    """Return (creating if necessary) the CircuitBreaker for *provider*."""
    if provider not in _breakers:
        _breakers[provider] = CircuitBreaker()
    return _breakers[provider]


def should_skip_provider(provider: str) -> bool:
    """Return True when the breaker for *provider* is open."""
    return breaker_for(provider).is_open()
