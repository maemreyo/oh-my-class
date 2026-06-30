from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


USED_TOKEN_PATTERN = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
DECLARED_TOKEN_PATTERN = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
DOC_TOKEN_PATTERN = re.compile(r"`(--[A-Za-z0-9_-]+)`")

SCANNED_ROOTS = (
    Path("apps/web/src/app"),
    Path("apps/web/src/components"),
    Path("packages/renderer/templates"),
    Path("packages/renderer/src"),
)

SCANNED_EXTENSIONS = {".css", ".html", ".ts", ".tsx"}
IGNORED_PATH_PARTS = {"__tests__", "dist", "node_modules"}


def test_used_css_variables_are_declared_by_design_sources() -> None:
    used = _used_tokens()
    declared = _declared_tokens()

    missing = sorted(used - declared)

    assert missing == []


def _used_tokens() -> set[str]:
    tokens: set[str] = set()
    for root in SCANNED_ROOTS:
        for file_path in _source_files(root):
            source = file_path.read_text(encoding="utf-8")
            source = re.sub(r"var\(\s*--c-<%=[^)]+\)", "", source)
            tokens.update(USED_TOKEN_PATTERN.findall(source))
    return tokens


def _declared_tokens() -> set[str]:
    tokens = set(DOC_TOKEN_PATTERN.findall(Path("DESIGN.md").read_text(encoding="utf-8")))
    for file_path in (
        Path("apps/web/src/app/globals.css"),
        Path("common/branding/kits/default/theme_default.css"),
        Path("common/branding/kits/ocean/theme_ocean.css"),
        Path("common/branding/kits/forest/theme_forest.css"),
    ):
        tokens.update(DECLARED_TOKEN_PATTERN.findall(file_path.read_text(encoding="utf-8")))
    for theme_path in Path("packages/renderer/src/theme/themes").glob("*.json"):
        tokens.update(_renderer_tokens_from_theme(json.loads(theme_path.read_text(encoding="utf-8"))))
    tokens.update(_inverse_thinking_local_tokens())
    tokens.update(_renderer_static_tokens())
    return tokens


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in SCANNED_EXTENSIONS:
            continue
        if IGNORED_PATH_PARTS.intersection(file_path.parts):
            continue
        files.append(file_path)
    return files


def _renderer_tokens_from_theme(theme: dict[str, Any]) -> set[str]:
    semantic = theme.get("semantic", {})
    category_colors = semantic.get("categoryColors", {})
    tokens = {
        "--color-bg",
        "--color-bg-card",
        "--color-bg-deep",
        "--color-text",
        "--color-text-soft",
        "--color-text-faint",
        "--color-border",
        "--color-border-soft",
        "--color-accent",
        "--color-accent-deep",
        "--color-accent-tint",
        "--color-success",
        "--color-warning",
        "--color-error",
        "--font-heading",
        "--font-body",
        "--font-mono",
    }
    if isinstance(category_colors, dict):
        for key in category_colors:
            tokens.add(f"--color-category-{key}")
            tokens.add(f"--color-category-{key}-tint")
    component = theme.get("component", {})
    if isinstance(component, dict):
        if "questionCardRadius" in component:
            tokens.add("--question-card-radius")
        if "questionCardShadow" in component:
            tokens.add("--question-card-shadow")
        if "flashcardHeight" in component:
            tokens.add("--flashcard-height")
        if "flashcardRadius" in component:
            tokens.add("--flashcard-radius")
    return tokens


def _inverse_thinking_local_tokens() -> set[str]:
    return {
        "--paper",
        "--ink",
        "--muted",
        "--line",
        "--accent",
        "--safe",
        "--clue",
    }


def _renderer_static_tokens() -> set[str]:
    return {
        "--surface",
        "--text",
        "--card",
        "--ink-soft",
        "--ink-faint",
        "--line-soft",
        "--red",
        "--red-deep",
        "--red-tint",
        "--gold",
        "--gold-tint",
        "--green",
        "--green-tint",
        "--radius",
        "--shadow",
        "--c-a",
        "--c-a-tint",
        "--c-b",
        "--c-b-tint",
        "--c-c",
        "--c-c-tint",
        "--c-d",
        "--c-d-tint",
        "--c-e",
        "--c-e-tint",
    }
