"""Standing report: list every ``# BLOCKED-ON:`` marker in the tree.

Informational only — always exits 0. A marker means code that's correctly
implemented but permanently unreachable pending external work (see the
``# BLOCKED-ON:`` convention documented in
``tests/test_no_dark_runtime_modules.py``, alongside ``KNOWN_DARK``). This
report just surfaces where those markers live and what they're waiting on,
so they don't get forgotten once the blocking work ships.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SCAN_DIRS: Final[tuple[str, ...]] = ("packages", "services")
MARKER: Final[str] = "# BLOCKED-ON:"


def find_markers() -> list[str]:
    hits: list[str] = []
    for scan_dir in SCAN_DIRS:
        for path in (ROOT / scan_dir).rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if "/tests/" in f"/{relative}":
                continue
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if MARKER in line:
                    hits.append(f"{relative}:{line_number}: {line.strip()}")
    return hits


def main() -> int:
    hits = find_markers()
    if not hits:
        print("No BLOCKED-ON markers found.")
        return 0
    print(f"{len(hits)} BLOCKED-ON marker(s):")
    print("\n".join(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
