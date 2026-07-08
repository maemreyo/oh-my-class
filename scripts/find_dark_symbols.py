"""Dark-code standing report: surface zero-caller symbols not yet triaged.

Informational companion to ``tests/test_no_dark_runtime_modules.py``. That test's
``REQUIRE_WIRED``/``KNOWN_DARK`` ledgers are a good self-maintaining mechanism
*once a symbol is in them* — but getting a symbol into them is manual. This
script walks ``packages/`` + ``services/`` for public top-level ``def``/``class``
symbols, reuses that test's own "caller" definition to count non-test runtime
references, and prints whatever has zero callers and isn't already in either
ledger.

Not a CI gate (see .scratch/llm-governance-hardening/LGH-07-dark-code-standing-report.md
for why) — run manually or from a non-blocking scheduled job. Always exits 0.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_no_dark_runtime_modules import (  # noqa: E402
    KNOWN_DARK,
    REQUIRE_WIRED,
    RUNTIME_ROOTS,
    _has_runtime_caller,
    _is_test_path,
)

# Module-level only (no leading indentation) — deliberately narrow to dodge
# nested defs, dataclass fields, and TypedDict keys that a looser regex would
# mistake for top-level symbols. `async def` counts too (this codebase is
# heavily async — missing it would silently drop most LLM/gateway coroutines).
DEF_RE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


def _public_top_level_symbols() -> list[tuple[str, str]]:
    """(symbol, defining_file_relative_to_repo_root) for public, non-test, non-__init__ defs."""
    found: list[tuple[str, str]] = []
    for base in RUNTIME_ROOTS:
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts or _is_test_path(path):
                continue
            if path.name == "__init__.py":  # re-exports, not definitions of interest
                continue
            rel = path.relative_to(ROOT).as_posix()
            for line in path.read_text(encoding="utf-8").splitlines():
                match = DEF_RE.match(line)
                if match and not match.group(1).startswith("_"):
                    found.append((match.group(1), rel))
    return found


def main() -> int:
    triaged = {symbol for symbol, _ in (*REQUIRE_WIRED, *KNOWN_DARK)}
    dark = sorted(
        (symbol, rel)
        for symbol, rel in _public_top_level_symbols()
        if symbol not in triaged and not _has_runtime_caller(symbol, rel)
    )

    if not dark:
        print("No new dark symbols — everything zero-caller is already triaged.")
        return 0

    print(f"{len(dark)} new zero-caller symbol(s) not yet in REQUIRE_WIRED/KNOWN_DARK:\n")
    for symbol, rel in dark:
        print(f"  {symbol}  ({rel})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
