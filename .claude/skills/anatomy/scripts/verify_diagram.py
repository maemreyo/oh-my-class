#!/usr/bin/env python3
"""
verify_diagram.py -- cross-checks system-diagram.md against modules/*.md,
for the end of Phase 5 of the anatomy skill's tracing workflow.

Usage:
    python3 verify_diagram.py <output_root>

<output_root> is docs/anatomy/ (or wherever the user pointed this run) --
the folder containing system-diagram.md and modules/*.md.

references/output-templates.md and references/tracing-methodology.md both
say every edge in the diagram should be traceable to a "Depends on" or
"Used by" line in a module doc, and vice versa -- that's what makes the
diagram trustworthy rather than just an illustration someone drew. Saying
"cross-check before finishing" is easy to skip under time pressure and easy
to do sloppily even with good intentions; this script checks it
mechanically instead. Run it after writing modules/*.md and
system-diagram.md, before considering Phase 5 done:

  python3 verify_diagram.py <output_root>

Reports three kinds of drift as JSON:

  - diagram_edges_unconfirmed: an edge drawn in the diagram that neither
    module doc backs up -- missing from both A's "Depends on" and B's
    "Used by". Usually means a module doc's "Depends on"/"Used by" section
    is missing an entry that should be there.
  - depends_on_missing_from_diagram: a module doc says A depends on B, but
    there's no A-->B edge in the diagram. Usually means the diagram is
    stale relative to the module docs.
  - depends_on_used_by_mismatch: A's doc says "Depends on B" but B's doc's
    "Used by" section doesn't list A (or vice versa) -- the two module docs
    disagree with each other, independent of the diagram entirely. This is
    exactly the kind of thing the "transpose Depends-on into Used-by" step
    in SKILL.md exists to prevent; a mismatch here usually means that step
    was skipped or done incompletely for one module.

An empty result (all three lists empty) means the diagram and the module
docs are internally consistent with each other. It does NOT mean any of it
is correct against the actual source code -- that's what Phase 4's reading
and verification is for. This script only catches drift between two pieces
of *output*, the same way a linter catches inconsistency without knowing
whether the code is right.

If something is flagged, don't just delete the offending line to make the
tool quiet -- open the relevant module(s) and check which side (the
diagram or the doc) actually reflects what Phase 4 confirmed, then fix
that side. A flagged edge is a prompt to look, not an automatic sign the
diagram is wrong.

Parses the specific Mermaid style this skill's own output-templates.md
generates: simple `id[label] --> id[label]` edges under a heading matching
"Module dependency graph". This is NOT a general-purpose Mermaid parser --
it deliberately ignores the "System Context" and sequence-diagram ("Key
flows") sections, since those involve non-module participants (end users,
external systems, "Client") that have no "Depends on"/"Used by" entry to
check against in the first place.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SECTION_HEADING_RE = re.compile(r"^#{1,6}\s*Module dependency graph", re.IGNORECASE)
ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
FENCE_START_RE = re.compile(r"^```\s*mermaid\s*$")
FENCE_END_RE = re.compile(r"^```\s*$")
# Matches `A[...] --> B[...]`, `A --> B[(...)]`, `A --> B`, tolerating the
# node-shape suffix ([...], ((...)), {...}) this skill's templates use.
EDGE_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9_-]+)\s*(?:\[[^\]]*\]|\(\([^)]*\)\)|\{[^}]*\})?"
    r"\s*-{1,3}>\s*"
    r"([A-Za-z0-9_-]+)"
)

DEPENDS_HEADING_RE = re.compile(r"^#{1,6}\s*Depends on", re.IGNORECASE)
USED_BY_HEADING_RE = re.compile(r"^#{1,6}\s*Used by", re.IGNORECASE)
MODULE_REF_RE = re.compile(r"\*\*`([^`]+)`\*\*")


def extract_module_graph_edges(text):
    """Pull (from, to) node-id pairs out of the mermaid block that sits
    under the 'Module dependency graph' heading -- and only that block."""
    edges = []
    in_section = in_fence = False
    for line in text.splitlines():
        if SECTION_HEADING_RE.match(line):
            in_section, in_fence = True, False
            continue
        if in_section and ANY_HEADING_RE.match(line) and not SECTION_HEADING_RE.match(line):
            in_section = in_fence = False
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if FENCE_START_RE.match(stripped):
            in_fence = True
            continue
        if in_fence and FENCE_END_RE.match(stripped):
            in_fence = False
            continue
        if in_fence:
            m = EDGE_LINE_RE.match(line)
            if m:
                edges.append((m.group(1), m.group(2)))
    return edges


def extract_refs(text, heading_re):
    """Pull module slugs referenced (as **`slug`**) under a given section
    heading -- used for both 'Depends on' and 'Used by' sections."""
    refs = set()
    in_section = False
    for line in text.splitlines():
        if heading_re.match(line):
            in_section = True
            continue
        if in_section and ANY_HEADING_RE.match(line):
            in_section = False
            continue
        if in_section:
            refs.update(MODULE_REF_RE.findall(line))
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root", help="path to docs/anatomy/ (or wherever the trace was written)")
    args = ap.parse_args()

    root = Path(args.output_root).resolve()
    diagram_path = root / "system-diagram.md"
    modules_dir = root / "modules"

    if not diagram_path.exists():
        print(json.dumps({"error": f"not found: {diagram_path}"}))
        sys.exit(1)
    if not modules_dir.is_dir():
        print(json.dumps({"error": f"not found: {modules_dir}"}))
        sys.exit(1)

    diagram_edges = set(extract_module_graph_edges(diagram_path.read_text(errors="ignore")))

    depends_on, used_by = {}, {}
    for md in sorted(modules_dir.glob("*.md")):
        slug = md.stem
        text = md.read_text(errors="ignore")
        depends_on[slug] = extract_refs(text, DEPENDS_HEADING_RE)
        used_by[slug] = extract_refs(text, USED_BY_HEADING_RE)

    doc_edges_depends = {(a, b) for a, targets in depends_on.items() for b in targets}
    doc_edges_used_by = {(a, b) for b, sources in used_by.items() for a in sources}

    diagram_edges_unconfirmed = sorted(
        e for e in diagram_edges
        if e not in doc_edges_depends and e not in doc_edges_used_by
    )
    depends_on_missing_from_diagram = sorted(doc_edges_depends - diagram_edges)
    mismatch = sorted(doc_edges_depends ^ doc_edges_used_by)

    def fmt(pairs):
        return [{"from": a, "to": b} for a, b in pairs]

    result = {
        "output_root": str(root),
        "modules_found": sorted(depends_on.keys()),
        "diagram_edges_unconfirmed": fmt(diagram_edges_unconfirmed),
        "depends_on_missing_from_diagram": fmt(depends_on_missing_from_diagram),
        "depends_on_used_by_mismatch": fmt(mismatch),
        "counts": {
            "diagram_edges": len(diagram_edges),
            "diagram_edges_unconfirmed": len(diagram_edges_unconfirmed),
            "depends_on_missing_from_diagram": len(depends_on_missing_from_diagram),
            "depends_on_used_by_mismatch": len(mismatch),
        },
        "note": (
            "Empty lists mean the diagram and module docs are internally "
            "consistent with each other -- this checks agreement between "
            "two pieces of output, not either one against the actual "
            "source code, which is Phase 4's job."
        ),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
