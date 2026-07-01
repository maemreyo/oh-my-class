from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (PROJECT_ROOT / "packages", PROJECT_ROOT / "services")
ALLOWED_SUFFIXES = (
    "packages/agents/tests/llm/test_transport_policy.py",
    "packages/agents/llm/transport.py",
)


def test_no_production_imports_legacy_llm_transport() -> None:
    offenders: list[str] = []

    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            if relative.endswith(ALLOWED_SUFFIXES):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if _imports_legacy_transport(tree):
                offenders.append(relative)

    assert offenders == []


def _imports_legacy_transport(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        match node:
            case ast.ImportFrom(module="packages.agents.llm.transport"):
                return True
            case ast.ImportFrom(module="packages.agents.llm"):
                if any(alias.name == "transport" for alias in node.names):
                    return True
            case ast.Import(names=names):
                if any(alias.name == "packages.agents.llm.transport" for alias in names):
                    return True
            case _:
                continue
    return False
