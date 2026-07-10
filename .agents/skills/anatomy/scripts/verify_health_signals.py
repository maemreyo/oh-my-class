#!/usr/bin/env python3
"""
verify_health_signals.py -- cross-checks index.md's "Codebase health
signals" section against a fresh run of rollup.py's computation over
modules/*.md, for the end of Phase 5 of the anatomy skill's tracing
workflow.

Usage:
    python3 verify_health_signals.py <output_root>

<output_root> is docs/anatomy/ (or wherever this run's output lives) --
the folder containing index.md and modules/*.md.

SKILL.md says index.md's "Codebase health signals" section is "populated
from scripts/rollup.py's output ... run it once, don't hand-count any of
this" -- but that's a written instruction, not something enforced. Nothing
previously checked that the prose Claude actually typed into index.md
matches what rollup.py, run fresh right now, would report. In practice
this drifts: rollup.py's real ranking gets hand-approximated, "none found"
gets written for cycles/orphans that do exist, or trace-coverage claims
outrun what the module docs' own footers say. This script is that missing
check, the same shape as verify_diagram.py (system-diagram.md vs module
docs) and verify_entry_points.py (entry-points.md vs module docs) --
except here the two sides being compared are index.md's prose and a fresh
rollup.py computation over the same modules/*.md.

Run it alongside the other two verify scripts, at the end of Phase 5,
before considering the phase done:

    python3 verify_diagram.py <output_root>
    python3 verify_entry_points.py <output_root>
    python3 verify_health_signals.py <output_root>

Reports drift as JSON, one finding per signal that disagrees:

  - most_connected: index.md's numbered ranking (as far as it lists
    modules) doesn't match rollup.py's ranking over the same prefix
    length.
  - orphan_candidates: index.md says "none found" but rollup.py finds
    some, or vice versa (index.md lists some but rollup.py finds none).
  - cycles: same shape, for "Dependency cycles."
  - trace_coverage: index.md's "<X> of <Y> modules were traced in full"
    claim doesn't match rollup.py's actual full/total counts.

An empty "findings" list means index.md's health-signals prose currently
agrees with a fresh rollup.py run over modules/*.md as they exist right
now. As with the other two verify scripts, that does NOT mean any of it
is correct against the actual source code -- only that this piece of
*output* wasn't hand-approximated or left stale relative to another piece
of output. If something is flagged, re-run `scripts/rollup.py
<output_root>` and copy its numbers into index.md's health-signals
section rather than hand-editing the prose to make this script quiet.

Parsing index.md's health-signals section is necessarily light heuristic
parsing of prose (unlike the tabular/fenced formats verify_diagram.py and
verify_entry_points.py parse) -- it recognizes the exact phrasing
output-templates.md's index.md template uses. If index.md's health-signals
section has drifted from that template's wording enough that this script
can't parse a given line at all, it reports that line as "unparsed" rather
than guessing, so a false-clean result doesn't hide a real mismatch.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rollup import (  # noqa: E402
    DEPENDS_HEADING_RE,
    USED_BY_HEADING_RE,
    extract_coverage,
    extract_refs,
    find_cycles,
)

SECTION_HEADING_RE = re.compile(r"^##\s*Codebase health signals", re.IGNORECASE)
ANY_H2_RE = re.compile(r"^##\s")
MOST_CONNECTED_ROW_RE = re.compile(r"^\s*\d+\.\s*`([^`]+)`")
BOLD_LABEL_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*)$")
NONE_FOUND_RE = re.compile(r"\bnone found\b", re.IGNORECASE)
TRACE_FULL_OF_RE = re.compile(r"(\d+)\s+of\s+(\d+)\s+modules\s+were\s+traced\s+in\s+full", re.IGNORECASE)


def parse_index_health_signals(text):
    """Light heuristic parse of index.md's health-signals section, matching
    output-templates.md's index.md template phrasing. Returns a dict with
    whatever it could confidently parse; missing/unparsed pieces are left
    as None rather than guessed at."""
    lines = text.splitlines()
    in_section = False
    most_connected = []
    orphans_line = None
    cycles_line = None
    trace_line = None
    for line in lines:
        if SECTION_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section and ANY_H2_RE.match(line):
            break
        if not in_section:
            continue
        m = MOST_CONNECTED_ROW_RE.match(line)
        if m:
            most_connected.append(m.group(1))
            continue
        m = BOLD_LABEL_RE.match(line.strip())
        if not m:
            continue
        label, rest = m.group(1).strip().lower(), m.group(2).strip()
        if label.startswith("possible dead code") or label.startswith("orphan"):
            orphans_line = rest
        elif label.startswith("dependency cycles"):
            cycles_line = rest
        elif label.startswith("trace coverage"):
            trace_line = rest

    trace_claim = None
    if trace_line is not None:
        tm = TRACE_FULL_OF_RE.search(trace_line)
        if tm:
            trace_claim = {"full_claimed": int(tm.group(1)), "total_claimed": int(tm.group(2))}

    return {
        "most_connected_order": most_connected,
        "orphans_line": orphans_line,
        "orphans_claims_none": (NONE_FOUND_RE.search(orphans_line) is not None) if orphans_line else None,
        "cycles_line": cycles_line,
        "cycles_claims_none": (NONE_FOUND_RE.search(cycles_line) is not None) if cycles_line else None,
        "trace_coverage_line": trace_line,
        "trace_coverage_claim": trace_claim,
    }


def compute_actual(modules_dir, top_n):
    """Same computation rollup.py does, duplicated rather than shelled out
    to, so this script gets a Python dict back instead of re-parsing JSON
    off stdout -- same small-duplication convention graph_export.py
    already follows for extract_coverage()."""
    depends_on, used_by, coverage = {}, {}, {}
    for md in sorted(modules_dir.glob("*.md")):
        slug = md.stem
        text = md.read_text(errors="ignore")
        depends_on[slug] = extract_refs(text, DEPENDS_HEADING_RE)
        used_by[slug] = extract_refs(text, USED_BY_HEADING_RE)
        status, _fragment = extract_coverage(text)
        coverage[slug] = status

    all_slugs = sorted(set(depends_on) | set(used_by))
    degree = {slug: len(depends_on.get(slug, ())) + len(used_by.get(slug, ())) for slug in all_slugs}
    most_connected = sorted(all_slugs, key=lambda s: (-degree[s], s))[:top_n]
    orphan_candidates = sorted(
        slug for slug in all_slugs if not depends_on.get(slug) and not used_by.get(slug)
    )
    graph = {slug: depends_on.get(slug, set()) & set(all_slugs) for slug in all_slugs}
    cycles = find_cycles(graph)
    coverage_counts = {"full": 0, "sampled": 0, "listed": 0, "unstated": 0}
    for status in coverage.values():
        coverage_counts[status] = coverage_counts.get(status, 0) + 1

    return {
        "most_connected_order": most_connected,
        "orphan_candidates": orphan_candidates,
        "cycles": [{"path": c, "length": len(c) - 1} for c in cycles],
        "coverage_counts": coverage_counts,
        "modules_found": len(all_slugs),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root", help="path to docs/anatomy/ (or wherever the trace was written)")
    args = ap.parse_args()

    root = Path(args.output_root).resolve()
    index_path = root / "index.md"
    modules_dir = root / "modules"
    if not index_path.is_file():
        print(json.dumps({"error": f"not found: {index_path}"}))
        sys.exit(1)
    if not modules_dir.is_dir():
        print(json.dumps({"error": f"not found: {modules_dir}"}))
        sys.exit(1)

    claimed = parse_index_health_signals(index_path.read_text(errors="ignore"))
    actual = compute_actual(modules_dir, top_n=max(len(claimed["most_connected_order"]), 5))

    findings = []

    if claimed["most_connected_order"]:
        actual_prefix = actual["most_connected_order"][: len(claimed["most_connected_order"])]
        if claimed["most_connected_order"] != actual_prefix:
            findings.append({
                "signal": "most_connected",
                "index_md_claims": claimed["most_connected_order"],
                "rollup_actual": actual_prefix,
            })
    else:
        findings.append({"signal": "most_connected", "issue": "unparsed -- no numbered rows found under the heading"})

    if claimed["orphans_claims_none"] is None:
        findings.append({"signal": "orphan_candidates", "issue": "unparsed -- 'Possible dead code / orphan modules' line not found or not in the expected format"})
    elif claimed["orphans_claims_none"] and actual["orphan_candidates"]:
        findings.append({
            "signal": "orphan_candidates",
            "index_md_claims": "none found",
            "rollup_actual": actual["orphan_candidates"],
        })
    elif not claimed["orphans_claims_none"] and not actual["orphan_candidates"]:
        findings.append({
            "signal": "orphan_candidates",
            "index_md_claims": claimed["orphans_line"],
            "rollup_actual": "none found",
        })

    if claimed["cycles_claims_none"] is None:
        findings.append({"signal": "cycles", "issue": "unparsed -- 'Dependency cycles' line not found or not in the expected format"})
    elif claimed["cycles_claims_none"] and actual["cycles"]:
        findings.append({
            "signal": "cycles",
            "index_md_claims": "none found",
            "rollup_actual": actual["cycles"],
        })
    elif not claimed["cycles_claims_none"] and not actual["cycles"]:
        findings.append({
            "signal": "cycles",
            "index_md_claims": claimed["cycles_line"],
            "rollup_actual": "none found",
        })

    if claimed["trace_coverage_claim"] is None:
        findings.append({"signal": "trace_coverage", "issue": "unparsed -- 'Trace coverage' line not found or not in the expected '<X> of <Y> modules were traced in full' format"})
    else:
        actual_full = actual["coverage_counts"]["full"]
        actual_total = actual["modules_found"]
        claim = claimed["trace_coverage_claim"]
        if claim["full_claimed"] != actual_full or claim["total_claimed"] != actual_total:
            findings.append({
                "signal": "trace_coverage",
                "index_md_claims": f"{claim['full_claimed']} of {claim['total_claimed']} traced in full",
                "rollup_actual": f"{actual_full} of {actual_total} traced in full (counts: {actual['coverage_counts']})",
            })

    result = {
        "output_root": str(root),
        "index_md_claims": claimed,
        "rollup_actual": actual,
        "findings": findings,
        "note": (
            "Empty findings means index.md's health-signals prose matches a fresh "
            "scripts/rollup.py computation over the current modules/*.md -- this checks "
            "agreement between two pieces of output, not either one against the actual "
            "source code, same spirit as verify_diagram.py/verify_entry_points.py. If "
            "something is flagged, re-run scripts/rollup.py and copy its numbers into "
            "index.md's health signals section rather than hand-editing them to make "
            "this script quiet."
        ),
    }
    print(json.dumps(result, indent=2))
    if findings:
        sys.exit(1)


if __name__ == "__main__":
    main()
