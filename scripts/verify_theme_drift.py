from __future__ import annotations

import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.branding.generate_theme import render_theme_css


THEMES = ("default", "ocean", "forest")
KIT_DIR = Path("common/branding/kits")


def main() -> int:
    failures: list[str] = []
    for theme in THEMES:
        expected = render_theme_css(theme, str(KIT_DIR))
        output_path = KIT_DIR / theme / f"theme_{theme}.css"
        actual = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if actual != expected:
            diff = "".join(
                difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=str(output_path),
                    tofile=f"generated:{theme}",
                )
            )
            failures.append(f"Theme CSS drift for {theme}:\n{diff}")
    if failures:
        sys.stderr.write("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
