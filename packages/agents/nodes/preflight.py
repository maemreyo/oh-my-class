"""Step 01 — Preflight: validate raw teacher input."""

from __future__ import annotations

from typing import Any

from packages.agents.nodes.state import NodeState


def step_01_preflight(state: NodeState) -> dict[str, Any]:
    """Validate raw_request is non-empty and structurally sound."""
    from packages.agents.config.gate_config import GateConfig
    config = GateConfig()
    raw = state.get("raw_request", "").strip()
    if not raw:
        raise ValueError("raw_request is required and cannot be empty")
    if len(raw) < config.preflight_min_length:
        raise ValueError(f"raw_request must be at least {config.preflight_min_length} characters")

    return {"current_step": 1}
