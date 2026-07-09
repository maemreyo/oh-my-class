"""CI gate for the system-trace documentation.

Fails the build if any `path:line` reference inside docs/system-trace/*.md points at a
non-existent file or an out-of-range line number. This enforces the "traced, not documented"
contract: every claim in the trace docs must be verifiable against real source.
"""
import os
import subprocess
import sys


def _repo_root() -> str:
    cur = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(cur, "AGENTS.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("repo root not found")
        cur = parent


def test_system_trace_refs():
    root = _repo_root()
    script = os.path.join(root, "scripts", "verify_doc_refs.py")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
