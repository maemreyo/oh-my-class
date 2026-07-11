from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
ANATOMY_DIR = ROOT / "docs" / "anatomy"
ANATOMY_SCRIPTS = ROOT / ".agents" / "skills" / "anatomy" / "scripts"

if str(ANATOMY_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ANATOMY_SCRIPTS))

from state import hash_module  # noqa: E402


class ModuleSnapshot(TypedDict):
    hash: str
    file_count: int


class AnatomyManifest(TypedDict):
    modules: dict[str, ModuleSnapshot]


def check_anatomy_freshness(root: Path = ROOT) -> list[str]:
    anatomy_dir = root / "docs" / "anatomy"
    manifest = _read_manifest(anatomy_dir / "_manifest.json")
    module_paths = _read_module_paths(anatomy_dir / "_modules.json")
    expected_modules = manifest["modules"]
    failures: list[str] = []

    for slug, relative_path in sorted(module_paths.items()):
        snapshot = hash_module(root, relative_path)
        expected = expected_modules.get(slug)
        if snapshot is None:
            failures.append(f"{slug}: traced path is missing: {relative_path}")
        elif expected is None:
            failures.append(f"{slug}: module is untracked in docs/anatomy/_manifest.json")
        elif snapshot["hash"] != expected["hash"]:
            failures.append(
                f"{slug}: source changed at {relative_path}; refresh docs/anatomy with /anatomy"
            )

    for slug in sorted(set(expected_modules) - set(module_paths)):
        failures.append(f"{slug}: manifest entry has no path in docs/anatomy/_modules.json")
    return failures


def _read_manifest(path: Path) -> AnatomyManifest:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_module_paths(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    failures = check_anatomy_freshness()
    if failures:
        print("STALE ANATOMY TRACE:")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("OK: docs/anatomy hashes match all traced modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
