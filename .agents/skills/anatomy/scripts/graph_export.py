#!/usr/bin/env python3
"""
graph_export.py -- writes docs/anatomy/_graph.json, a persisted,
machine-readable snapshot of the whole system graph, for the end of Phase 5
of the anatomy skill's tracing workflow.

Usage:
    python3 graph_export.py <output_root> [--top-n 10]

<output_root> is docs/anatomy/ (or wherever this run's output lives) -- the
folder containing modules/*.md and entry-points.md. Run this after
entry-points.md and module docs are written, same point in Phase 5 as
rollup.py, verify_diagram.py, and verify_entry_points.py -- it re-parses the
same already-written output those scripts do, so it should run after all of
them, not instead of them.

Why this exists, distinct from rollup.py: rollup.py prints health-signal
numbers to stdout for index.md's "Codebase health signals" section and
nothing else persists to disk. Every other output file in docs/anatomy/ is
prose for a human to read. Nothing captures the whole module/edge/
entry-point graph as a single structured artifact another tool (or a future
run of this skill, or a different repo's run, in a multi-repo setup) could
consume without re-parsing five different Markdown files by hand. This
script writes that artifact: <output_root>/_graph.json.

Like rollup.py, this is purely a re-parse of already-written output -- it
does not re-read source code or re-verify anything against it. Everything
in _graph.json is only as correct as the module docs and entry-points.md it
was extracted from (which is what Phase 4's discipline and
verify_diagram.py/verify_entry_points.py are for).

Schema (version 1) -- see references/output-templates.md's "_graph.json"
section for the authoritative version of this:

{
  "version": 1,
  "generated_at": "<ISO8601>",
  "source_root": "<abs path at export time>",
  "modules": {
    "<slug>": {
      "path": "<relative path, from _modules.json if present, else null>",
      "depends_on": [
        {"target": "other-module", "kind": "internal"|"external",
         "detail": "<bullet text minus the citation>",
         "citation": "<path:line, or null if not present on that line>"}
      ],
      "used_by": [ <same shape as depends_on> ],
      "trace_coverage": {"status": "full"|"sampled"|"listed"|"unstated",
                          "detail": "<raw matched fragment, or null>"}
    }
  },
  "entry_points": {
    "http_routes": [{"module": "...", "detail": "<path>", "raw": "<full row>"}],
    "cli_commands": [ <same shape> ],
    "queue_consumers": [ <same shape -- "detail" is the topic/event name,
                          the join key a future multi-repo run would match
                          a publisher in one repo to a consumer in another> ],
    "cron_jobs": [ <same shape> ]
  },
  "health_signals": {
    "most_connected": [...],
    "orphan_candidates": [...],
    "cycles": [...],
    "trace_coverage_counts": {"full": N, "sampled": N, "listed": N, "unstated": N}
  }
}

Known limitations (v1, worth knowing before leaning on this for something
load-bearing):
  - "depends_on"/"used_by" internal/external classification is purely a
    convention check (does the bullet start with "**`slug`**" or
    "external:`name`" per output-templates.md's template) -- a module doc
    that doesn't follow the template's exact bullet format won't be
    captured here, the same brittleness rollup.py already has.
  - Outbound cross-service calls (an HTTP client hitting another service,
    a gRPC stub) don't currently have a guaranteed structured field the way
    queue topics do -- they show up as prose inside a "Depends on" bullet's
    "detail" text if written as an external dependency, or inside "Data &
    side effects" -> "Network calls" if not, neither of which this script
    tries to further parse into a URL. queue_consumers' topic names are the
    one entry-point kind with a clean, already-tabular join key today; HTTP
    routes only capture the path this repo *serves*, not URLs it *calls*.
    A future multi-repo pass will likely need external_calls.py's own
    hypothesis output (URLs/topics it detects) folded in here directly,
    not just what survived into module-doc prose -- noted for whoever picks
    up the multi-repo direction next, not solved by this script.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_entry_points import extract_entry_point_rows  # noqa: E402

DEPENDS_HEADING_RE = re.compile(r"^#{1,6}\s*Depends on", re.IGNORECASE)
USED_BY_HEADING_RE = re.compile(r"^#{1,6}\s*Used by", re.IGNORECASE)
ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
INTERNAL_LINE_RE = re.compile(r"^\s*-\s+\*\*`([^`]+)`\*\*\s*--\s*(.*)$")
EXTERNAL_LINE_RE = re.compile(r"^\s*-\s+external:\s*`([^`]+)`\s*--\s*(.*)$")
TRAILING_CITATION_RE = re.compile(r"\(`([^`]+)`\)\s*\.?\s*$")

FOOTER_RE = re.compile(r"Files examined in depth:\s*(.+?)\.?\s*$", re.IGNORECASE)
SAMPLED_RE = re.compile(r"sampled\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
ALL_N_RE = re.compile(r"\ball\s+(\d+)\s+files?\b", re.IGNORECASE)


def extract_edges(text, heading_re):
    """Same section-scoping as rollup.py's extract_refs, but keeps the full
    bullet (target, kind, detail, citation) instead of collapsing to a bare
    set of slugs -- that richer shape is the whole point of this script."""
    edges = []
    in_section = False
    for line in text.splitlines():
        if heading_re.match(line):
            in_section = True
            continue
        if in_section and ANY_HEADING_RE.match(line) and not heading_re.match(line):
            in_section = False
            continue
        if not in_section:
            continue
        m = INTERNAL_LINE_RE.match(line)
        kind = "internal"
        if not m:
            m = EXTERNAL_LINE_RE.match(line)
            kind = "external"
        if not m:
            continue
        target, rest = m.group(1).strip(), m.group(2).strip()
        cm = TRAILING_CITATION_RE.search(rest)
        citation = cm.group(1) if cm else None
        detail = TRAILING_CITATION_RE.sub("", rest).strip().rstrip(".").strip()
        edges.append({"target": target, "kind": kind, "detail": detail, "citation": citation})
    return edges


def extract_coverage(text):
    """Identical logic to rollup.py's extract_coverage -- duplicated rather
    than imported, same convention the other Phase-5 scripts already
    follow (see verify_diagram.py/verify_entry_points.py each defining
    their own small heading/line regexes independently)."""
    m = FOOTER_RE.search(text)
    if not m:
        return "unstated", None
    fragment = m.group(1).strip()
    fragment = fragment.rstrip("*_")
    fragment = fragment.rstrip(".")
    fragment = fragment.rstrip("*_")
    fragment = fragment.strip()
    if ALL_N_RE.search(fragment):
        return "full", fragment
    if SAMPLED_RE.search(fragment):
        return "sampled", fragment
    return "listed", fragment


def find_cycles(graph, cap=25):
    """Same DFS as rollup.py's find_cycles."""
    cycles = []
    visited = set()
    stack = []
    on_stack = set()

    def dfs(node):
        if len(cycles) >= cap:
            return
        visited.add(node)
        stack.append(node)
        on_stack.add(node)
        for nxt in sorted(graph.get(node, ())):
            if len(cycles) >= cap:
                break
            if nxt in on_stack:
                start = stack.index(nxt)
                cycles.append(stack[start:] + [nxt])
            elif nxt not in visited:
                dfs(nxt)
        stack.pop()
        on_stack.discard(node)

    for node in sorted(graph.keys()):
        if node not in visited and len(cycles) < cap:
            dfs(node)
    return cycles


def load_module_paths(output_root):
    """_modules.json is the persisted copy of Phase 2's slug->path mapping
    (see SKILL.md Phase 6). Optional -- an older docs/anatomy/ written
    before this file existed simply won't have "path" filled in below."""
    p = output_root / "_modules.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root", help="path to docs/anatomy/ (or wherever the trace was written)")
    ap.add_argument("--top-n", type=int, default=10, help="how many modules to list under most_connected")
    ap.add_argument("--write", action="store_true",
                     help="write _graph.json into output_root instead of only printing to stdout")
    args = ap.parse_args()

    root = Path(args.output_root).resolve()
    modules_dir = root / "modules"
    if not modules_dir.is_dir():
        print(json.dumps({"error": f"not found: {modules_dir}"}))
        sys.exit(1)

    module_paths = load_module_paths(root)

    modules = {}
    for md in sorted(modules_dir.glob("*.md")):
        slug = md.stem
        text = md.read_text(errors="ignore")
        depends_on = extract_edges(text, DEPENDS_HEADING_RE)
        used_by = extract_edges(text, USED_BY_HEADING_RE)
        status, fragment = extract_coverage(text)
        modules[slug] = {
            "path": module_paths.get(slug),
            "depends_on": depends_on,
            "used_by": used_by,
            "trace_coverage": {"status": status, "detail": fragment},
        }

    entry_points_path = root / "entry-points.md"
    entry_points = {"http_routes": [], "cli_commands": [], "queue_consumers": [], "cron_jobs": []}
    if entry_points_path.is_file():
        ep_text = entry_points_path.read_text(errors="ignore")
        for row in extract_entry_point_rows(ep_text):
            entry_points.setdefault(row["kind"], []).append(
                {"module": row["module"], "detail": row["detail"], "raw": row["raw"]}
            )

    # Health signals: same computation as rollup.py, restricted to
    # "internal" edges only -- external libs shouldn't count toward
    # module-to-module degree/cycles, matching rollup.py's original
    # behavior (its MODULE_REF_RE never matched "external:" lines either).
    internal_depends = {
        slug: {e["target"] for e in info["depends_on"] if e["kind"] == "internal"}
        for slug, info in modules.items()
    }
    internal_used_by = {
        slug: {e["target"] for e in info["used_by"] if e["kind"] == "internal"}
        for slug, info in modules.items()
    }
    all_slugs = sorted(modules.keys())
    degree = {
        slug: len(internal_depends.get(slug, ())) + len(internal_used_by.get(slug, ()))
        for slug in all_slugs
    }
    most_connected = sorted(
        (
            {"module": slug, "depends_on_count": len(internal_depends.get(slug, ())),
             "used_by_count": len(internal_used_by.get(slug, ())), "total_degree": degree[slug]}
            for slug in all_slugs
        ),
        key=lambda r: (-r["total_degree"], r["module"]),
    )[: args.top_n]
    orphan_candidates = sorted(
        slug for slug in all_slugs
        if not internal_depends.get(slug) and not internal_used_by.get(slug)
    )
    graph = {slug: internal_depends.get(slug, set()) & set(all_slugs) for slug in all_slugs}
    raw_cycles = find_cycles(graph)
    cycles = [{"path": c, "length": len(c) - 1} for c in raw_cycles]

    coverage_counts = {"full": 0, "sampled": 0, "listed": 0, "unstated": 0}
    for info in modules.values():
        status = info["trace_coverage"]["status"]
        coverage_counts[status] = coverage_counts.get(status, 0) + 1

    result = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_root": str(root),
        "modules": modules,
        "entry_points": entry_points,
        "health_signals": {
            "most_connected": most_connected,
            "orphan_candidates": orphan_candidates,
            "cycles": cycles,
            "trace_coverage_counts": coverage_counts,
        },
    }

    if args.write:
        out_path = root / "_graph.json"
        out_path.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"written": str(out_path), "modules_found": len(modules)}, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()