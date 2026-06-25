"""Layer 4: Mark for human escalation."""
from __future__ import annotations

from typing import Any


def apply(state: dict[str, Any], fail_count: int) -> dict[str, Any]:
    """Mark for human escalation. Notifications handled by NotificationSystem."""
    fail_layer = state.get("fail_layer", "unknown")
    fail_context = state.get("fail_context") or {}
    errors = fail_context.get("errors", ["unknown"])

    return {
        "fail_count": fail_count,
        "healing_strategy": "escalate",
        "escalate": True,
        "escalate_reason": (
            f"Auto-escalated after {fail_count} failed healing attempts. "
            f"Last fail layer: {fail_layer}. "
            f"Last error: {errors}"
        ),
        "error": f"Escalated: {fail_layer} gate failed {fail_count} times",
    }
