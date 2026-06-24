"""Lead Agent prompt loader — reads markdown files from this directory."""

from __future__ import annotations

from pathlib import Path


def load_system_prompt(name: str = "system") -> str:
    """Load a prompt from the prompts/ directory."""
    path = Path(__file__).parent / f"{name}.md"
    return path.read_text(encoding="utf-8")
