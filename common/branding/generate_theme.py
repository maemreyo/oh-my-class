"""Theme generator — reads theme.json and generates theme_*.css files."""

from __future__ import annotations

import json
import os
from pathlib import Path


def generate_theme(theme_name: str, kit_dir: str) -> str:
    """Generate CSS from theme.json.

    Args:
        theme_name: Theme name (default, ocean, forest).
        kit_dir: Path to branding kits directory.

    Returns:
        Generated CSS content.
    """
    theme_path = Path(kit_dir) / theme_name / "theme.json"

    if not theme_path.exists():
        raise FileNotFoundError(f"Theme not found: {theme_path}")

    with open(theme_path, encoding="utf-8") as f:
        theme_data = json.load(f)

    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    typography = theme_data.get("typography", {})
    border_radius = theme_data.get("border-radius", theme_data.get("borderRadius", {}))

    css = f"""/* Auto-generated from theme.json — DO NOT EDIT MANUALLY */
/* Theme: {theme_name} */

:root {{
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

    /* Typography */
    --font-family: {typography.get('font-family', "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif")};
    --font-size-sm: {typography.get('font-size-sm', '14px')};
    --font-size-base: {typography.get('font-size-base', '16px')};
    --font-size-lg: {typography.get('font-size-lg', '18px')};
    --font-size-xl: {typography.get('font-size-xl', '24px')};
    --line-height: {typography.get('line-height', '1.6')};

    /* Border radius */
    --radius-sm: {border_radius.get('sm', '4px')};
    --radius-md: {border_radius.get('md', '8px')};
    --radius-lg: {border_radius.get('lg', '12px')};
}}

body {{
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    line-height: var(--line-height);
    color: var(--color-text);
    background-color: var(--color-background);
    margin: 0;
    padding: 0;
}}
"""

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
