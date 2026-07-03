from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = (ROOT / "packages", ROOT / "services", ROOT / "tests")
REMOVED_STATE_FILE = ROOT / "packages/agents/state.py"
REMOVED_SYMBOLS = (
    "Oh" + "MyClassState",
    "packages.agents.state",
    "from packages.agents import merge_artifacts",
)
ALLOWED_SCAN_FILES = {Path(__file__).resolve()}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for path in SCAN_PATHS:
        files.extend(
            file_path
            for file_path in path.rglob("*.py")
            if "__pycache__" not in file_path.parts and file_path not in ALLOWED_SCAN_FILES
        )
    return files


def test_legacy_state_module_is_removed() -> None:
    assert not REMOVED_STATE_FILE.exists()


def test_runtime_does_not_reference_legacy_state_symbols() -> None:
    offenders: list[str] = []
    for file_path in _python_files():
        source = file_path.read_text(encoding="utf-8")
        for symbol in REMOVED_SYMBOLS:
            if symbol in source:
                offenders.append(f"{file_path.relative_to(ROOT)} references {symbol}")

    assert offenders == []
