from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Final


_PRODUCTION_ROOTS: Final = ("apps", "common", "packages", "services")
_PRODUCTION_SUFFIXES: Final = (".py", ".ts", ".tsx")
_IGNORED_PARTS: Final = (
    "__pycache__",
    "__snapshots__",
    "__tests__",
    "alembic",
    "generated",
    "migrations",
    "tests",
)
_TEST_MARKERS: Final = ("test", "tests", "__tests__")


@dataclass(frozen=True, slots=True)
class ComponentAddition:
    path: PurePosixPath

    @property
    def module_stem(self) -> str:
        return self.path.stem.removeprefix("test_").removesuffix(".test")


def missing_component_tests(
    added_paths: list[str],
    all_paths: list[str],
    changed_paths: list[str],
) -> list[str]:
    existing_tests = [PurePosixPath(path) for path in all_paths if _is_test_path(PurePosixPath(path))]
    changed_tests = [PurePosixPath(path) for path in changed_paths if _is_test_path(PurePosixPath(path))]
    missing: list[str] = []
    for added in _added_components(added_paths):
        if not _has_test_for(added, existing_tests, changed_tests):
            missing.append(str(added.path))
    return missing


def _added_components(paths: list[str]) -> list[ComponentAddition]:
    return [
        ComponentAddition(path=path)
        for raw_path in paths
        if _is_production_component(path := PurePosixPath(raw_path))
    ]


def _has_test_for(
    added: ComponentAddition,
    existing_tests: list[PurePosixPath],
    changed_tests: list[PurePosixPath],
) -> bool:
    candidate_tests = existing_tests + changed_tests
    return any(_test_matches_component(added, test_path) for test_path in candidate_tests)


def _test_matches_component(added: ComponentAddition, test_path: PurePosixPath) -> bool:
    test_name = test_path.name
    return added.module_stem in test_name or test_name.startswith(f"test_{added.module_stem}")


def _is_production_component(path: PurePosixPath) -> bool:
    if path.parts == () or path.parts[0] not in _PRODUCTION_ROOTS:
        return False
    if path.suffix not in _PRODUCTION_SUFFIXES:
        return False
    return not any(part in _IGNORED_PARTS for part in path.parts)


def _is_test_path(path: PurePosixPath) -> bool:
    return any(part in _TEST_MARKERS for part in path.parts) or path.name.startswith("test_")


def _git_lines(args: list[str]) -> list[str]:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _merge_base() -> str | None:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if not base_ref:
        return None
    candidates = [f"origin/{base_ref}", base_ref]
    for candidate in candidates:
        try:
            return _git_lines(["git", "merge-base", "HEAD", candidate])[0]
        except (subprocess.CalledProcessError, IndexError):
            continue
    return None


def main() -> int:
    base = _merge_base()
    if base is None:
        return 0
    added_paths = _git_lines(["git", "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD"])
    changed_paths = _git_lines(["git", "diff", "--name-only", f"{base}...HEAD"])
    all_paths = _git_lines(["git", "ls-files"])
    missing = missing_component_tests(added_paths, all_paths, changed_paths)
    if missing == []:
        return 0
    print("New production components need a matching test file:", file=sys.stderr)
    for path in missing:
        print(f"- {path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
