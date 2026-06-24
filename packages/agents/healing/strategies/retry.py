"""Layer 0: Exponential backoff with ±25% jitter."""
from __future__ import annotations
import random
import time


def apply(state: dict, fail_count: int) -> dict:
    """Exponential backoff with ±25% jitter. Same inputs, retry immediately."""
    base_delay = 0.5
    max_delay = 10.0
    delay = min(base_delay * (2 ** (fail_count - 1)), max_delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    time.sleep(max(0.0, delay + jitter))

    return {
        "fail_count": fail_count,
        "healing_strategy": "retry",
        "healing_note": f"Retrying after {delay:.1f}s backoff (attempt {fail_count})",
    }
