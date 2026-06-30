from __future__ import annotations

import ast
from pathlib import Path

ROUTERS_DIR = Path(__file__).resolve().parents[1] / "routers"
ALLOWED_UNSCOPED_RUN_ACCESS: frozenset[tuple[str, str]] = frozenset({
    ("notifications.py", "get_run_summary"),
    ("notifications.py", "recover_run"),
    ("teaching_pack_deps.py", "get_run_with_ownership"),
    ("teaching_pack_deps.py", "get_deleted_run_with_ownership"),
})


def test_teacher_facing_routers_do_not_call_unscoped_get_run_by_id() -> None:
    violations = sorted(_unscoped_run_accessor_calls() - ALLOWED_UNSCOPED_RUN_ACCESS)

    assert violations == []


def _unscoped_run_accessor_calls() -> set[tuple[str, str]]:
    calls: set[tuple[str, str]] = set()
    for path in ROUTERS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            if _calls_get_run_by_id(node):
                calls.add((path.name, node.name))
    return calls


def _calls_get_run_by_id(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    return any(
        isinstance(child, ast.Attribute) and child.attr == "get_run_by_id"
        for child in ast.walk(node)
    )
