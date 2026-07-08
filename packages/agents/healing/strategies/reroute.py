"""Layer 2: Swap model — escalate to the configured strong tier, if one exists."""
from __future__ import annotations

from typing import Any

from packages.agents.config.models import MODELS

DEFAULT_GENERATION_MODEL = "4omc"


def apply(state: dict[str, Any], fail_count: int) -> dict[str, Any]:
    """Escalate to MODELS.strong_default when a real stronger tier is configured.

    In a single-model deployment (no MODEL_STRONG_DEFAULT override — the common
    case today), strong_default equals DEFAULT_GENERATION_MODEL, so there is no
    second model to reroute to. This holds the current model steady instead of
    swapping to a fabricated model name that no router would recognize.
    """
    current_model = state.get("generation_model") or DEFAULT_GENERATION_MODEL
    strong = MODELS.strong_default or DEFAULT_GENERATION_MODEL
    fallback = strong if current_model != strong else current_model

    note = (
        f"Switching model: {current_model} → {fallback}"
        if fallback != current_model
        else f"No stronger model configured beyond {current_model}; holding steady."
    )

    return {
        "fail_count": fail_count,
        "healing_strategy": "reroute",
        "generation_model": fallback,
        "healing_note": note,
        "artifacts": None,
    }
