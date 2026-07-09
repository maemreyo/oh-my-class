#!/usr/bin/env python3
"""
import_graph.py -- heuristic cross-file reference extraction, for Phase 3 of
system-trace.

Usage:
    python3 import_graph.py <repo_root> [--group-by-top-level]

Prints JSON to stdout: a per-file list of raw import/require/use targets,
plus (with --group-by-top-level) a rolled-up edge count between top-level
directories, e.g. {"from": "api", "to": "services", "count": 12}.

THIS IS A HYPOTHESIS GENERATOR, NOT A GROUND TRUTH. Regexes cannot know
whether an imported name is actually called, called once or in a hot loop,
or dead-imported and unused. Every edge this script reports must be opened
and confirmed in the actual source before it goes into a module doc or
diagram -- see references/tracing-methodology.md. What this script is good
for: telling you where to look, fast, across a codebase too large to grep
through file-by-file by hand.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import walk_source_files  # noqa: E402

# Each pattern captures one imported target per match, in the first non-None
# group. Deliberately simple line-based regexes -- good enough to hypothesize
# an edge, not meant to fully resolve module systems (aliasing, re-exports,
# dynamic imports, etc. will be missed; that's expected and fine).
PATTERNS = {
    ".py": [re.compile(r"^\s*from\s+([\w\.]+)\s+import"), re.compile(r"^\s*import\s+([\w\.]+)")],
    ".js": [re.compile(r"from\s+['\"]([^'\"]+)['\"]"), re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")],
    ".jsx": None, ".ts": None, ".tsx": None, ".mjs": None, ".cjs": None,  # filled below
    ".go": [re.compile(r'^\s*"([^"]+)"')],  # applied only inside import(...) blocks, see extract_go
    ".rs": [re.compile(r"^\s*use\s+([\w:]+)")],
    ".java": [re.compile(r"^\s*import\s+(?:static\s+)?([\w\.]+)\s*;")],
    ".kt": [re.compile(r"^\s*import\s+([\w\.]+)")],
    ".rb": [re.compile(r"require(?:_relative)?\s+['\"]([^'\"]+)['\"]")],
    ".php": [re.compile(r"use\s+([\w\\]+)\s*;"), re.compile(r"(?:require|include)(?:_once)?\s*\(?\s*['\"]([^'\"]+)['\"]")],
    ".cs": [re.compile(r"^\s*using\s+([\w\.]+)\s*;")],
}
for alias in (".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
    PATTERNS[alias] = PATTERNS[".js"]


def extract_go_imports(text: str):
    targets = []
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("import ("):
            in_block = True
            continue
        if in_block:
            if s == ")":
                in_block = False
                continue
            m = re.match(r'"([^"]+)"', s)
            if m:
                targets.append(m.group(1))
        elif s.startswith("import "):
            m = re.search(r'"([^"]+)"', s)
            if m:
                targets.append(m.group(1))
    return targets


def extract_imports(path: Path):
    suffix = path.suffix.lower()
    if suffix not in PATTERNS:
        return []
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return []

    if suffix == ".go":
        return extract_go_imports(text)

    targets = []
    for line in text.splitlines():
        for pat in PATTERNS[suffix]:
            m = pat.search(line)
            if m:
                targets.append(m.group(1))
    return targets


def top_level_of(rel_path: Path):
    parts = rel_path.parts
    return parts[0] if len(parts) > 1 else "(root)"


def resolve_target_to_top_level(target: str, all_top_levels):
    """Very rough: if an import string contains a top-level dir name as a
    path segment or dotted segment, guess that's the target module. Misses
    absolute-package-name imports (e.g. importing a pip package that happens
    to share a name) -- Claude should sanity check ambiguous edges, not take
    the grouped counts as gospel."""
    normalized = target.replace(".", "/").replace("\\", "/")
    segments = [s for s in normalized.split("/") if s]
    for seg in segments:
        if seg in all_top_levels:
            return seg
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("--group-by-top-level", action="store_true")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    per_file = []
    top_levels_seen = set()

    files = list(walk_source_files(repo_root))
    for abs_path, rel_path in files:
        if len(rel_path.parts) > 1:
            top_levels_seen.add(rel_path.parts[0])

    for abs_path, rel_path in files:
        targets = extract_imports(abs_path)
        if targets:
            per_file.append({"file": str(rel_path), "imports": targets})

    result = {"repo_root": str(repo_root), "per_file": per_file}

    if args.group_by_top_level:
        edge_counts = {}
        for entry in per_file:
            src_top = top_level_of(Path(entry["file"]))
            for t in entry["imports"]:
                dst_top = resolve_target_to_top_level(t, top_levels_seen)
                if dst_top and dst_top != src_top:
                    key = (src_top, dst_top)
                    edge_counts[key] = edge_counts.get(key, 0) + 1
        edges = [{"from": a, "to": b, "count": c} for (a, b), c in sorted(edge_counts.items(), key=lambda kv: -kv[1])]
        result["top_level_edges"] = edges
        result["note"] = (
            "top_level_edges is a heuristic hypothesis grouped by first path "
            "segment. Verify meaningful edges by opening the actual call sites "
            "before writing them into module docs or diagrams."
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
