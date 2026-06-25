"""Step 01 — Preflight: validate raw teacher input."""

from __future__ import annotations

from typing import Any

from packages.agents.state import (
    OhMyClassState,  # noqa: TC001  needed at runtime for LangGraph get_type_hints
)


def step_01_preflight(state: OhMyClassState) -> dict[str, Any]:
    """Validate raw_request is non-empty and structurally sound.

    Rejects: empty strings, whitespace-only, shorter than 10 chars.
    Sets current_step = 1.
    """
    raw = state.get("raw_request", "").strip()
    if not raw:
        raise ValueError("raw_request is required and cannot be empty")
    if len(raw) < 10:
        raise ValueError("raw_request must be at least 10 characters")

    return {"current_step": 1}
