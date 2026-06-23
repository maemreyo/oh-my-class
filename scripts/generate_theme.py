"""Generate CSS custom properties from theme.json files.

Single source of truth: common/branding/kits/{name}/theme.json
Output: packages/renderer/branding/theme_{name}.css
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

KITS_DIR = Path("common/branding/kits")
OUTPUT_DIR = Path("packages/renderer/branding")


def generate_css(theme_name: str, theme_data: dict[str, Any]) -> str:
    """Convert theme.json to CSS custom properties."""
    lines = [
        f"/* Auto-generated from {theme_name}/theme.json — DO NOT EDIT MANUALLY */",
        f"/* Theme: {theme_name} */",
        "",
        ":root {",
    ]

    def flatten(obj: dict[str, Any], prefix: str = "") -> None:
        for key, value in obj.items():
            var_name = f"--omc-{prefix}{key}" if prefix else f"--omc-{key}"
            if isinstance(value, dict):
                flatten(value, f"{key}-")
            else:
                lines.append(f"  {var_name}: {value};")

    flatten(theme_data)
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for kit_dir in KITS_DIR.iterdir():
        if kit_dir.is_dir():
            theme_json = kit_dir / "theme.json"
            if theme_json.exists():
                data = json.loads(theme_json.read_text())
                css = generate_css(kit_dir.name, data)
                output_file = OUTPUT_DIR / f"theme_{kit_dir.name}.css"
                output_file.write_text(css)
                print(f"Generated {output_file}")


if __name__ == "__main__":
    main()
