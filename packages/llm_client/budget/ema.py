"""Exponential Moving Average tracker for token usage per task type."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EMATracker:
    """Tracks EMA of token usage. Uses fixed default until min_samples collected."""

    alpha: float = 0.1          # smaller = slower to adapt, more stable
    min_samples: int = 5        # require N samples before trusting EMA

    _values: dict[str, float] = field(default_factory=dict, repr=False)
    _counts: dict[str, int] = field(default_factory=dict, repr=False)

    def record(self, task: str, tokens: int) -> None:
        """Record actual token usage for a task."""
        count = self._counts.get(task, 0)
        current = self._values.get(task, float(tokens))

        if count == 0:
            self._values[task] = float(tokens)
        else:
            self._values[task] = self.alpha * tokens + (1 - self.alpha) * current

        self._counts[task] = count + 1

    def get_ema(self, task: str) -> float | None:
        """Return EMA value if enough samples collected, else None."""
        if self._counts.get(task, 0) < self.min_samples:
            return None
        return self._values.get(task)

    def sample_count(self, task: str) -> int:
        return self._counts.get(task, 0)
