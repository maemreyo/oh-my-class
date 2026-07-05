"""Layer 1: Inject error context into generation prompt, same model."""
from __future__ import annotations

from typing import Any


def apply(state: dict[str, Any], fail_count: int) -> dict[str, Any]:
    """Inject error context into generation prompt, same model."""
    fail_context = state.get("fail_context") or {}
    errors = fail_context.get("errors", [])
    error_summary = "; ".join(str(e) for e in errors[:3])

    healing_context = dict(state.get("healing_context") or {})
    healing_context["rewrite_instruction"] = (
        f"Previous attempt failed validation. Fix these issues:\n{error_summary}"
    )

    return {
        "fail_count": fail_count,
        "healing_strategy": "rewrite",
        "healing_context": healing_context,
        "artifacts": [],
    }
