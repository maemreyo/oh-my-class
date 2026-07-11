"""CI gate for the anatomy documentation.

Fails the build if any `path:line` reference inside docs/anatomy/*.md points at a
non-existent file or an out-of-range line number. This enforces the "traced, not documented"
contract: every claim in the trace docs must be verifiable against real source.
"""
import os
import subprocess
import sys
from pathlib import Path

from scripts.verify_doc_refs import check_md


def _repo_root() -> str:
    cur = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(cur, "AGENTS.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("repo root not found")
        cur = parent


def test_anatomy_refs():
    root = _repo_root()
    script = os.path.join(root, "scripts", "verify_doc_refs.py")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_anatomy_refs_resolve_gateway_relative_handler(tmp_path: Path) -> None:
    handler = tmp_path / "services" / "gateway" / "routers" / "handlers.py"
    handler.parent.mkdir(parents=True)
    handler.write_text("def handle() -> None:\n    pass\n", encoding="utf-8")
    docs = tmp_path / "entry-points.md"
    docs.write_text("`routers/handlers.py:1`\n", encoding="utf-8")

    assert check_md(str(docs), str(tmp_path)) == []
