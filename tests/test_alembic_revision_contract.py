from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

VERSIONS_DIR = Path("services/gateway/alembic/versions")
MAX_VERSION_NUM_LENGTH = 32
TARGET_MIGRATION = VERSIONS_DIR / "041_run_event_outbox_and_tenant_scope.py"
EXPECTED_TARGET_REVISION = "041_run_event_outbox_tenant"


def _assignment(module: ast.Module, name: str) -> Any:
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"missing {name!r} assignment")


def _revision(path: Path) -> str:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = _assignment(module, "revision")
    assert isinstance(value, str) and value, f"{path}: revision must be a non-empty string"
    return value


def test_alembic_revision_ids_fit_default_version_table() -> None:
    revisions: dict[str, Path] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        revision = _revision(path)
        assert len(revision) <= MAX_VERSION_NUM_LENGTH, (
            f"{path}: revision {revision!r} has {len(revision)} characters; "
            f"Alembic version_num allows {MAX_VERSION_NUM_LENGTH}"
        )
        assert revision not in revisions, (
            f"duplicate Alembic revision {revision!r}: {revisions.get(revision)} and {path}"
        )
        revisions[revision] = path


def test_run_event_outbox_revision_uses_persistable_identifier() -> None:
    assert _revision(TARGET_MIGRATION) == EXPECTED_TARGET_REVISION
