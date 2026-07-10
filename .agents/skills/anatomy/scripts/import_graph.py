#!/usr/bin/env python3
"""
import_graph.py -- heuristic cross-file reference extraction, for Phase 3 of
the anatomy skill's tracing workflow. See external_calls.py for the
complementary script that covers cross-service/network interactions this
one can't see (it only catches same-language import/require/use statements).

Usage:
    python3 import_graph.py <repo_root> [--group-by-top-level] [--modules modules.json]

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

--modules <modules.json>: pass Phase 2's slug -> relative-path mapping (the
same file scripts/state.py hash-modules consumes) to group edges by actual
module boundary instead of guessing from the first path segment. Without
this flag, grouping falls back to "first directory segment under repo
root" -- which is wrong for any project with a wrapping directory before
the real module dirs (`src/api`, `src/services`, `app/controllers`, ...:
one of module-detection.md's own documented shapes). In that layout every
file's first segment is the same wrapper ("src"), so the fallback collapses
every module into one bucket and reports zero cross-module edges even when
real ones exist. Pass --modules whenever Phase 2 has already produced
modules.json (it normally has, by the time Phase 3 runs) to get accurate
grouping instead; the fallback exists only for a first look before module
boundaries are decided.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    walk_source_files, load_module_map, resolve_module_for_path,
    resolve_relative_import,
)

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
    ".swift": [re.compile(r"^\s*(?:@testable\s+)?import\s+([\w\.]+)")],
    ".dart": [re.compile(r"^\s*(?:import|export|part)\s+['\"]([^'\"]+)['\"]")],
    ".scala": [re.compile(r"^\s*import\s+([\w\.{}, ]+)")],
    ".ex": [re.compile(r"^\s*(?:alias|import|use|require)\s+([\w\.]+)")],
    ".c": [re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]')],
    ".h": [re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]')],
    ".cpp": None, ".cc": None, ".cxx": None, ".hpp": None,  # filled below
}
for alias in (".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
    PATTERNS[alias] = PATTERNS[".js"]
for alias in (".cpp", ".cc", ".cxx", ".hpp"):
    PATTERNS[alias] = PATTERNS[".c"]
PATTERNS[".exs"] = PATTERNS[".ex"]
# Note on C/C++: this captures both `#include "local.h"` and
# `#include <system_header.h>` -- resolve_target_to_top_level() below only
# matches targets against actual top-level dir names, so angle-bracket
# system/library headers just won't resolve to anything and are harmlessly
# ignored, same as an unresolvable Python stdlib/pip import already is.
# Note on Scala: the capture group can include brace-list imports (e.g.
# `import foo.bar.{A, B}`) as one raw string -- resolve_target_to_top_level
# still finds a top-level segment fine since it splits on "." and "/", but
# don't expect a single clean package name out of this one.


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
    the grouped counts as gospel. This is the no-`--modules` fallback path;
    see resolve_target_to_module for the module-map-aware version used when
    `--modules` is given."""
    normalized = target.replace(".", "/").replace("\\", "/")
    segments = [s for s in normalized.split("/") if s]
    for seg in segments:
        if seg in all_top_levels:
            return seg
    return None


def resolve_target_to_module(source_rel_path: str, target: str, module_map, all_slugs):
    """Module-map-aware version of resolve_target_to_top_level, used when
    --modules is given. Two cases:

    - Relative import ('./x', '../services/order'): resolve it against the
      importing file's own directory to get a real repo-relative path, then
      find which declared module owns that path via longest-prefix match.
      This is the case the plain top-level-segment heuristic gets wrong
      whenever there's a wrapping directory (src/, app/, lib/) -- resolving
      the path properly instead of pattern-matching the raw string is what
      fixes it.
    - Dotted/bare target (Python 'pkg.sub.mod', Java 'com.acme.services.X',
      or a bare package name): fall back to segment-matching against known
      module *slugs* (not raw top-level dir names) -- still a guess, but a
      slightly better-informed one now that real module names are known.
    """
    resolved_path = resolve_relative_import(source_rel_path, target)
    if resolved_path is not None:
        parts = tuple(Path(resolved_path).parts)
        return resolve_module_for_path(parts, module_map)
    normalized = target.replace(".", "/").replace("\\", "/")
    segments = [s for s in normalized.split("/") if s]
    for seg in segments:
        if seg in all_slugs:
            return seg
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("--group-by-top-level", action="store_true")
    ap.add_argument(
        "--modules", default=None,
        help="path to Phase 2's modules.json (slug -> relative-path); when "
             "given, --group-by-top-level groups by actual module boundary "
             "instead of guessing from the first path segment",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    per_file = []
    top_levels_seen = set()
    module_map = load_module_map(args.modules)
    all_slugs = {slug for _parts, slug in module_map} if module_map else set()

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
        unmapped_files = set()
        for entry in per_file:
            rel_path = Path(entry["file"])
            if module_map is not None:
                src = resolve_module_for_path(rel_path.parts, module_map)
                if src is None:
                    unmapped_files.add(entry["file"])
                    continue
            else:
                src = top_level_of(rel_path)
            for t in entry["imports"]:
                if module_map is not None:
                    dst = resolve_target_to_module(entry["file"], t, module_map, all_slugs)
                else:
                    dst = resolve_target_to_top_level(t, top_levels_seen)
                if dst and dst != src:
                    key = (src, dst)
                    edge_counts[key] = edge_counts.get(key, 0) + 1
        edges = [{"from": a, "to": b, "count": c} for (a, b), c in sorted(edge_counts.items(), key=lambda kv: -kv[1])]
        result["top_level_edges"] = edges
        if module_map is not None:
            result["note"] = (
                "top_level_edges is a heuristic hypothesis grouped by the "
                "module boundaries in --modules (longest-prefix match on each "
                "file's path, with relative imports resolved against the "
                "importing file's own directory). Verify meaningful edges by "
                "opening the actual call sites before writing them into "
                "module docs or diagrams."
            )
            if unmapped_files:
                result["unmapped_files"] = sorted(unmapped_files)
                result["note"] += (
                    " unmapped_files lists source files that fell outside "
                    "every path in --modules (e.g. root-level config/entry "
                    "files) -- excluded from top_level_edges' 'from' side "
                    "since they have no owning module to attribute an edge to."
                )
        else:
            result["note"] = (
                "top_level_edges is a heuristic hypothesis grouped by first "
                "path segment under repo root -- this is wrong for a project "
                "with a wrapping directory (src/, app/, lib/) before its real "
                "module dirs, since every file's first segment is then the "
                "same wrapper. Re-run with --modules <modules.json> once "
                "Phase 2's module boundaries are decided for accurate "
                "grouping. Verify meaningful edges by opening the actual call "
                "sites before writing them into module docs or diagrams."
            )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()