"""Layer 0: Exponential backoff with ±25% jitter."""
from __future__ import annotations

import random
import time
from typing import Any


def apply(state: dict[str, Any], fail_count: int) -> dict[str, Any]:
    """Exponential backoff with ±25% jitter. Same inputs, retry immediately."""
    from packages.agents.config.gate_config import GateConfig
    config = GateConfig()
    base_delay = config.healing_base_delay_s
    max_delay = config.healing_max_delay_s
    delay = min(base_delay * (2 ** (fail_count - 1)), max_delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    time.sleep(max(0.0, delay + jitter))

    return {
        "fail_count": fail_count,
        "healing_strategy": "retry",
        "healing_note": f"Retrying after {delay:.1f}s backoff (attempt {fail_count})",
    }
