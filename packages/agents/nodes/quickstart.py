"""Step 02 — Quickstart: initialize run metadata."""

from __future__ import annotations

from typing import Any

from packages.agents.nodes.state import NodeState


def step_02_quickstart(state: NodeState) -> dict[str, Any]:
    """Initialize run metadata for downstream steps.

    Sets default artifact types, theme, and research policy if not already set.
    Sets current_step = 2.
    """
    updates: dict[str, Any] = {"current_step": 2}

    if not state.get("artifact_types"):
        updates["artifact_types"] = ["lesson", "worksheet", "quiz"]
    if not state.get("theme"):
        updates["theme"] = "default"
    if not state.get("research_policy"):
        updates["research_policy"] = "standard"

    return updates
