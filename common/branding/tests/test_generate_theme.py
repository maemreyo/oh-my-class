"""Tests for generate_theme — CSS theme generator."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from common.branding.generate_theme import generate_all_themes, generate_theme  # noqa: E402


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_kit_dir(themes: dict[str, dict]) -> str:
    """Create a temporary kit directory with theme.json files."""
    tmp = tempfile.mkdtemp()
    for name, data in themes.items():
        theme_dir = Path(tmp) / name
        theme_dir.mkdir()
        (theme_dir / "theme.json").write_text(json.dumps(data))
    return tmp


def _default_theme_data() -> dict:
    return {
        "colors": {
            "primary": "#4F46E5",
            "secondary": "#0EA5E9",
            "accent": "#F59E0B",
            "background": "#FFFFFF",
            "surface": "#F8FAFC",
            "text": "#1E293B",
            "text-secondary": "#64748B",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "typography": {
            "font-family": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
            "font-size-base": "16px",
            "font-size-sm": "14px",
            "font-size-lg": "18px",
            "font-size-xl": "24px",
            "line-height": "1.6",
        },
        "spacing": {
            "xs": "4px",
            "sm": "8px",
            "md": "16px",
            "lg": "24px",
            "xl": "32px",
        },
        "border-radius": {
            "sm": "4px",
            "md": "8px",
            "lg": "12px",
        },
    }


# ── generate_theme ────────────────────────────────────────────────────────────

class TestGenerateTheme:
    def test_returns_css_string(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert isinstance(css, str)

    def test_css_contains_root_block(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert ":root {" in css or ":root{" in css

    def test_css_contains_primary_color(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert "--color-primary: #4F46E5" in css

    def test_css_contains_font_family(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert "--font-family:" in css

    def test_css_contains_spacing_variables(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert "--space-xs:" in css
        assert "--space-md:" in css
        assert "--space-xl:" in css

    def test_css_contains_border_radius_variables(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert "--radius-sm:" in css
        assert "--radius-md:" in css
        assert "--radius-lg:" in css

    def test_css_contains_semantic_tokens(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert "--color-success:" in css
        assert "--color-error:" in css

    def test_css_contains_theme_comment(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        assert "default" in css

    def test_raises_for_missing_theme(self):
        kit_dir = _make_kit_dir({})
        with pytest.raises(FileNotFoundError, match="Theme not found"):
            generate_theme("nonexistent", kit_dir)

    def test_writes_css_file(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        generate_theme("default", kit_dir)
        output_path = Path(kit_dir) / "default" / "theme_default.css"
        assert output_path.exists()
        content = output_path.read_text()
        assert "--color-primary:" in content

    def test_written_file_matches_return_value(self):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        css = generate_theme("default", kit_dir)
        output_path = Path(kit_dir) / "default" / "theme_default.css"
        assert output_path.read_text() == css

    def test_uses_fallback_defaults_for_missing_keys(self):
        minimal_data = {"colors": {}}
        kit_dir = _make_kit_dir({"minimal": minimal_data})
        css = generate_theme("minimal", kit_dir)
        assert "--color-primary: #3b82f6" in css

    def test_uses_custom_color_values(self):
        custom_data = {"colors": {"primary": "#FF0000"}}
        kit_dir = _make_kit_dir({"custom": custom_data})
        css = generate_theme("custom", kit_dir)
        assert "--color-primary: #FF0000" in css


# ── generate_all_themes ───────────────────────────────────────────────────────

class TestGenerateAllThemes:
    def test_returns_dict(self):
        kit_dir = _make_kit_dir({
            "default": _default_theme_data(),
            "ocean": _default_theme_data(),
            "forest": _default_theme_data(),
        })
        result = generate_all_themes(kit_dir)
        assert isinstance(result, dict)

    def test_returns_all_three_themes(self):
        kit_dir = _make_kit_dir({
            "default": _default_theme_data(),
            "ocean": _default_theme_data(),
            "forest": _default_theme_data(),
        })
        result = generate_all_themes(kit_dir)
        assert set(result.keys()) == {"default", "ocean", "forest"}

    def test_skips_missing_themes(self, capsys):
        kit_dir = _make_kit_dir({"default": _default_theme_data()})
        result = generate_all_themes(kit_dir)
        assert "default" in result
        assert "ocean" not in result
        assert "forest" not in result

    def test_each_theme_is_valid_css(self):
        kit_dir = _make_kit_dir({
            "default": _default_theme_data(),
            "ocean": _default_theme_data(),
            "forest": _default_theme_data(),
        })
        result = generate_all_themes(kit_dir)
        for _theme_name, css in result.items():
            assert ":root {" in css or ":root{" in css
            assert "--color-primary:" in css

    def test_returns_empty_dict_when_no_themes(self):
        kit_dir = _make_kit_dir({})
        result = generate_all_themes(kit_dir)
        assert result == {}
