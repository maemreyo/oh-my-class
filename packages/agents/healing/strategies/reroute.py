"""Layer 2: Swap model — f.light → 4omc or vice versa."""
from __future__ import annotations

from typing import Any

DEFAULT_GENERATION_MODEL = "4omc"


def apply(state: dict[str, Any], fail_count: int) -> dict[str, Any]:
    """Swap model: if was using f.light → upgrade to 4omc."""
    current_model = state.get("generation_model") or DEFAULT_GENERATION_MODEL
    fallback = "4omc" if current_model == "f.light" else "f.light"

    return {
        "fail_count": fail_count,
        "healing_strategy": "reroute",
        "generation_model": fallback,
        "healing_note": f"Switching model: {current_model} → {fallback}",
        "artifacts": None,
    }
