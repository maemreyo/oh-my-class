"""CircuitBreaker — prevents cascading failures."""
from __future__ import annotations
import time


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    """Prevents cascading failures by stopping calls after threshold failures."""

    def __init__(self, threshold: int = 3, recovery_timeout: float = 60.0):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "closed"   # closed | open | half-open
        self.last_failure_time = 0.0

    def call(self, fn, *args, **kwargs):
        if self.state == "open":
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError(
                    f"Circuit open — wait {self.recovery_timeout:.0f}s before retry"
                )
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def _on_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "open"
