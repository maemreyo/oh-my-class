"""Step 05 — Pack Scope: determine artifact types for this run."""

from __future__ import annotations

from typing import Any

from packages.agents.nodes.state import NodeState

# Default artifact types when none specified
DEFAULT_ARTIFACT_TYPES = ["lesson", "worksheet", "quiz"]

# All supported artifact types
SUPPORTED_ARTIFACT_TYPES = {"lesson", "worksheet", "quiz", "drill", "recap", "infographic"}


def step_05_pack_scope(state: NodeState) -> dict[str, Any]:
    """Determine artifact types from request context and defaults.

    Uses existing artifact_types if set by quickstart, otherwise falls back to defaults.
    Validates all types are supported.
    """
    artifact_types = state.get("artifact_types") or DEFAULT_ARTIFACT_TYPES

    # Filter to only supported types
    valid_types = [t for t in artifact_types if t in SUPPORTED_ARTIFACT_TYPES]

    if not valid_types:
        valid_types = DEFAULT_ARTIFACT_TYPES.copy()

    return {
        "artifact_types": valid_types,
        "current_step": 5,
    }
