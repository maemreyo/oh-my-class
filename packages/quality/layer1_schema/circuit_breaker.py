"""Circuit breaker pattern for Layer 1 schema validation.

Prevents infinite retry loops by tracking consecutive failures.
After threshold consecutive failures, the circuit opens and blocks
further attempts for a cooldown period.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation — requests pass through
    OPEN = "open"  # Tripped — requests are blocked
    HALF_OPEN = "half_open"  # Testing — one request allowed through


@dataclass
class CircuitBreaker:
    """Circuit breaker for schema validation retries.

    Tracks consecutive failures. When threshold is reached, circuit opens
    and blocks further attempts. After cooldown, transitions to half-open
    to test if the issue is resolved.

    Args:
        threshold: Number of consecutive failures before opening circuit.
        cooldown_seconds: Seconds to wait before attempting half-open.
    """

    threshold: int = 3
    cooldown_seconds: float = 30.0

    # Internal state
    _failure_count: int = field(default=0, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _last_failure_time: float | None = field(default=None, repr=False)

    @property
    def state(self) -> CircuitState:
        """Current circuit state, with automatic transition logic."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful validation. Resets failure count."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed validation. Increments failure count."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.threshold:
            self._state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if a request is allowed through the circuit.

        Returns:
            True if the circuit is CLOSED or HALF_OPEN.
            False if the circuit is OPEN (blocked).
        """
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
