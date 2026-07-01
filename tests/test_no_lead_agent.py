from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATHS = (ROOT / "packages", ROOT / "services", ROOT / "tests")
REMOVED_SYMBOLS = ("make_lead_agent", "lead_agent_node")
REMOVED_MODULES = (
    ROOT / "packages/agents/lead_agent/agent.py",
    ROOT / "packages/agents/lead_agent/node.py",
    ROOT / "packages/agents/lead_agent/state.py",
)
ALLOWED_SCAN_FILES = {Path(__file__).resolve()}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for path in RUNTIME_PATHS:
        files.extend(
            file_path
            for file_path in path.rglob("*.py")
            if "__pycache__" not in file_path.parts and file_path not in ALLOWED_SCAN_FILES
        )
    return files


def test_dead_lead_agent_bridge_modules_are_removed() -> None:
    for module_path in REMOVED_MODULES:
        assert not module_path.exists(), f"dead Lead Agent bridge remains: {module_path}"


def test_runtime_does_not_import_removed_lead_agent_symbols() -> None:
    offenders: list[str] = []
    for file_path in _python_files():
        source = file_path.read_text(encoding="utf-8")
        for symbol in REMOVED_SYMBOLS:
            if symbol in source:
                offenders.append(f"{file_path.relative_to(ROOT)} references {symbol}")

    assert offenders == []


def test_prod_compose_does_not_depend_on_host_9router_service() -> None:
    prod_compose = ROOT / "infra/compose/docker-compose.prod.yml"
    source = prod_compose.read_text(encoding="utf-8")

    assert "9router" not in source
    assert "router:" not in source
