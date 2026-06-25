"""Step 06 — Visual Engine: choose theme, layout, visual treatments."""

from __future__ import annotations

from typing import Any

from packages.agents.state import (
    OhMyClassState,  # noqa: TC001  needed at runtime for LangGraph get_type_hints
)

SUPPORTED_THEMES = {"default", "ocean", "forest"}


def step_06_visual_engine(state: OhMyClassState) -> dict[str, Any]:
    """Select theme and visual treatments for the teaching pack.

    Validates theme is supported, falls back to default if not.
    """
    theme = state.get("theme", "default")

    if theme not in SUPPORTED_THEMES:
        theme = "default"

    return {
        "theme": theme,
        "current_step": 6,
    }
