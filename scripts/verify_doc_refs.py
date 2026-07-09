#!/usr/bin/env python3
"""Verify every `path:line` (and `path:start-end`) reference inside docs/system-trace/*.md.

The system-trace documentation was produced by TRACING the source code, not by reading
AGENTS.md. This script is the integrity gate: every `file:line` claim must point at a real
file and a line number inside that file's range. Any broken reference fails the run.

Usage:
    python scripts/verify_doc_refs.py
    pytest tests/test_system_trace_refs.py -q

The regex matches tokens like:
    packages/agents/teaching_pack/graph.py:32
    services/gateway/main.py:144-146
It requires a known source extension, so prose like `http://litellm:4000` or `localhost:8001`
is ignored. Paths that are explicitly described as missing (no `:line`) are also ignored.
"""
from __future__ import annotations

import os
import re
import sys

# Extensions we treat as citable source files.
_EXT = r"(?:py|ts|tsx|yml|yaml|json|md)"
_REF_RE = re.compile(r"([A-Za-z0-9_./\-]+\." + _EXT + r"):(\d+)(?:-(\d+))?")


def find_repo_root(start: str) -> str | None:
    cur = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(cur, "AGENTS.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def check_md(md_path: str, repo_root: str) -> list[tuple[str, str]]:
    """Return list of (reference, reason) for broken references."""
    broken: list[tuple[str, str]] = []
    with open(md_path, encoding="utf-8") as fh:
        text = fh.read()
    for m in _REF_RE.finditer(text):
        ref_path, start_s, end_s = m.group(1), m.group(2), m.group(3)
        if ref_path.startswith("/") or "://" in ref_path:
            continue
        abs_path = os.path.join(repo_root, ref_path)
        if not os.path.isfile(abs_path):
            broken.append((m.group(0), f"file not found: {ref_path}"))
            continue
        with open(abs_path, encoding="utf-8", errors="ignore") as ff:
            n_lines = sum(1 for _ in ff)
        start = int(start_s)
        end = int(end_s) if end_s else start
        if start < 1 or start > n_lines or end < 1 or end > n_lines:
            broken.append(
                (m.group(0), f"line range {start}-{end} out of range (file has {n_lines} lines): {ref_path}")
            )
    return broken


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = find_repo_root(here)
    if repo_root is None:
        print("ERROR: repo root (AGENTS.md) not found", file=sys.stderr)
        return 2
    doc_dir = os.path.join(repo_root, "docs", "system-trace")
    if not os.path.isdir(doc_dir):
        print(f"ERROR: {doc_dir} not found", file=sys.stderr)
        return 2

    all_broken: list[tuple[str, str, str]] = []
    for name in sorted(os.listdir(doc_dir)):
        if not name.endswith(".md"):
            continue
        for ref, why in check_md(os.path.join(doc_dir, name), repo_root):
            all_broken.append((name, ref, why))

    if all_broken:
        print(f"BROKEN REFERENCES: {len(all_broken)}")
        for name, ref, why in all_broken:
            print(f"  {name}: {ref} -> {why}")
        return 1
    print(f"OK: all doc path:line references resolve ({doc_dir}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
