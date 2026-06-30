"""Theme generator — reads theme.json and generates theme_*.css files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Default group colors used when theme_data has no 'groups' key.
_DEFAULT_GROUPS: dict[str, str] = {
    "a": "#33508F",
    "b": "#B9762A",
    "c": "#3C7A4E",
    "d": "#1F7A8C",
    "e": "#8A4F7E",
}


def load_theme_json(theme_path: Path) -> dict[str, Any]:
    """Load theme JSON from disk.

    Args:
        theme_path: Absolute path to theme.json.

    Returns:
        Parsed theme data dict.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not theme_path.exists():
        raise FileNotFoundError(f"Theme not found: {theme_path}")
    with open(theme_path, encoding="utf-8") as f:
        return json.load(f)


def generate_core_tokens(theme_data: dict[str, Any]) -> str:
    """Generate :root { } block with color, spacing, and border-radius tokens.

    Args:
        theme_data: Parsed theme data dict.

    Returns:
        CSS string for the core tokens block.
    """
    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    border_radius = theme_data.get("border-radius", theme_data.get("borderRadius", {}))

    return f""":root {{
    /* Primitives — color */
    --color-primary: {colors.get('primary', '#3b82f6')};
    --color-primary-light: {colors.get('primary-light', '#818cf8')};
    --color-secondary: {colors.get('secondary', '#10b981')};
    --color-accent: {colors.get('accent', '#f59e0b')};
    --color-background: {colors.get('background', '#ffffff')};
    --color-surface: {colors.get('surface', '#f8fafc')};
    --color-text: {colors.get('text', '#1e293b')};
    --color-text-secondary: {colors.get('text-secondary', '#64748b')};

    /* Semantic tokens */
    --color-success: {colors.get('success', '#10b981')};
    --color-warning: {colors.get('warning', '#f59e0b')};
    --color-error: {colors.get('error', '#ef4444')};

    /* Spacing */
    --space-xs: {spacing.get('xs', '4px')};
    --space-sm: {spacing.get('sm', '8px')};
    --space-md: {spacing.get('md', '16px')};
    --space-lg: {spacing.get('lg', '24px')};
    --space-xl: {spacing.get('xl', '32px')};

    /* Border radius */
    --radius-sm: {border_radius.get('sm', '4px')};
    --radius-md: {border_radius.get('md', '8px')};
    --radius-lg: {border_radius.get('lg', '12px')};
}}
"""


def _tint_hex(hex_color: str) -> str:
    """Return a lightened (tint) version of a hex color (blend 80% toward white)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    tr = r + round((255 - r) * 0.8)
    tg = g + round((255 - g) * 0.8)
    tb = b + round((255 - b) * 0.8)
    return f"#{tr:02X}{tg:02X}{tb:02X}"


def generate_group_tokens(theme_data: dict[str, Any]) -> str:
    """Generate --c-a through --c-e and tint variables inside :root { }.

    If the theme_data dict has no 'groups' key, falls back to default colors.

    Args:
        theme_data: Parsed theme data dict.

    Returns:
        CSS string for the group token :root block.
    """
    raw_groups = theme_data.get("groups", {})
    group_colors: dict[str, str] = {}
    for key, default_color in _DEFAULT_GROUPS.items():
        if key in raw_groups:
            group_colors[key] = raw_groups[key].get("color", default_color)
        else:
            group_colors[key] = default_color

    lines = [":root {", "    /* Group color tokens */"]
    for key, color in group_colors.items():
        lines.append(f"    --c-{key}: {color};")
    lines.append("")
    lines.append("    /* Group tint tokens */")
    for key, color in group_colors.items():
        lines.append(f"    --c-{key}-tint: {_tint_hex(color)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def generate_typography_tokens(theme_data: dict[str, Any]) -> str:
    """Generate typography custom properties inside :root { }.

    Args:
        theme_data: Parsed theme data dict.

    Returns:
        CSS string for the typography token :root block.
    """
    typography = theme_data.get("typography", {})
    font_family = typography.get(
        "font-family", "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    )
    font_size_base = typography.get("font-size-base", "16px")
    font_size_sm = typography.get("font-size-sm", "14px")
    font_size_lg = typography.get("font-size-lg", "18px")
    font_size_xl = typography.get("font-size-xl", "24px")
    line_height = typography.get("line-height", "1.6")

    return f""":root {{
    /* Typography */
    --font-family: {font_family};
    --font-size-sm: {font_size_sm};
    --font-size-base: {font_size_base};
    --font-size-lg: {font_size_lg};
    --font-size-xl: {font_size_xl};
    --line-height: {line_height};
}}
"""


def generate_utility_classes(theme_data: dict[str, Any]) -> str:
    """Generate .g-a through .g-e utility classes.

    Each class sets border-left-color and styles .qnum and .pc-id children.
    If the theme_data dict has no 'groups' key, falls back to default colors.

    Args:
        theme_data: Parsed theme data dict.

    Returns:
        CSS string for group utility classes.
    """
    raw_groups = theme_data.get("groups", {})
    group_colors: dict[str, str] = {}
    for key, default_color in _DEFAULT_GROUPS.items():
        if key in raw_groups:
            group_colors[key] = raw_groups[key].get("color", default_color)
        else:
            group_colors[key] = default_color

    blocks: list[str] = ["/* Group utility classes */"]
    for key, color in group_colors.items():
        tint = _tint_hex(color)
        blocks.append(
            f""".g-{key} {{
    border-left-color: {color};
}}

.g-{key} .qnum {{
    background-color: {color};
    color: #ffffff;
}}

.g-{key} .pc-id {{
    background-color: {tint};
    color: {color};
}}"""
        )

    return "\n\n".join(blocks) + "\n"


def generate_dark_mode(theme_data: dict[str, Any]) -> str:  # noqa: ARG001
    """Generate dark mode media query block.

    Args:
        theme_data: Parsed theme data dict (unused; dark mode overrides are fixed).

    Returns:
        CSS string for the dark mode media query.
    """
    return """@media (prefers-color-scheme: dark) {
    :root {
        --paper: #1a1a2e;
        --color-background: #1a1a2e;
        --color-surface: #16213e;
        --color-text: #e2e8f0;
        --color-text-secondary: #94a3b8;
    }
}
"""


def generate_print_styles(theme_data: dict[str, Any]) -> str:  # noqa: ARG001
    """Generate print media query block.

    Args:
        theme_data: Parsed theme data dict (unused; print styles are fixed).

    Returns:
        CSS string for the print media query.
    """
    return """@media print {
    .sidebar, .no-print {
        display: none;
    }

    .shell {
        display: block;
    }

    body {
        font-size: 12pt;
    }

    @page {
        margin: 2cm;
    }
}
"""


def render_theme_css(theme_name: str, kit_dir: str) -> str:
    """Render CSS from theme.json without writing it to disk.

    Args:
        theme_name: Theme name (default, ocean, forest).
        kit_dir: Path to branding kits directory.

    Returns:
        Generated CSS content.
    """
    theme_path = Path(kit_dir) / theme_name / "theme.json"
    theme_data = load_theme_json(theme_path)

    parts: list[str] = [
        f"/* Auto-generated from theme.json — DO NOT EDIT MANUALLY */\n/* Theme: {theme_name} */\n",
        generate_core_tokens(theme_data),
        generate_group_tokens(theme_data),
        generate_typography_tokens(theme_data),
        generate_utility_classes(theme_data),
        generate_dark_mode(theme_data),
        generate_print_styles(theme_data),
        """body {
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    line-height: var(--line-height);
    color: var(--color-text);
    background-color: var(--color-background);
    margin: 0;
    padding: 0;
}
""",
    ]

    css = "\n".join(parts)

    return css


def generate_theme(theme_name: str, kit_dir: str) -> str:
    """Generate CSS from theme.json and write it beside the source theme.

    Args:
        theme_name: Theme name (default, ocean, forest).
        kit_dir: Path to branding kits directory.

    Returns:
        Generated CSS content.
    """
    css = render_theme_css(theme_name, kit_dir)

    output_path = Path(kit_dir) / theme_name / f"theme_{theme_name}.css"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(css)

    return css


def generate_all_themes(kit_dir: str) -> dict[str, str]:
    """Generate CSS for all themes in the kit directory.

    Args:
        kit_dir: Path to branding kits directory.

    Returns:
        Dict mapping theme name to generated CSS.
    """
    themes: dict[str, str] = {}
    for theme_name in ["default", "ocean", "forest"]:
        try:
            css = generate_theme(theme_name, kit_dir)
            themes[theme_name] = css
        except FileNotFoundError:
            print(f"Theme {theme_name} not found, skipping")

    return themes


if __name__ == "__main__":
    kit_dir = os.path.join(os.path.dirname(__file__), "kits")
    themes = generate_all_themes(kit_dir)
    print(f"Generated {len(themes)} themes")
