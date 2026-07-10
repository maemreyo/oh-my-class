#!/usr/bin/env python3
"""
verify_entry_points.py -- cross-checks entry-points.md against modules/*.md
"Public interface" sections, for the end of Phase 5 of the anatomy skill's
tracing workflow.

Usage:
    python3 verify_entry_points.py <output_root>

<output_root> is docs/anatomy/ (or wherever this run's output lives) -- the
folder containing entry-points.md and modules/*.md.

references/output-templates.md says entry-points.md is "lifted from each
module's Public interface section" -- the exact same relationship
system-diagram.md has to modules/*.md's "Depends on"/"Used by" sections,
which is what motivated verify_diagram.py. This script is that same check
applied to the other file with the same drift risk: run it alongside
verify_diagram.py at the end of Phase 5, before considering the phase done.

  python3 verify_entry_points.py <output_root>

Reports two kinds of drift as JSON:

  - entry_points_unconfirmed: a row in entry-points.md (an HTTP route, CLI
    command, queue consumer, or cron job) whose identifying detail doesn't
    appear anywhere in its module's "Public interface" section -- either
    the module doc is missing it, or entry-points.md drifted from the
    module doc it was supposedly lifted from.
  - public_interface_uncaptured: a "Public interface" bullet in a module
    doc that looks like a route, cron schedule, or queue
    consumer/publisher, but whose identifying detail doesn't appear
    anywhere in entry-points.md -- usually means the Phase 5 rollup missed
    it when entry-points.md was written or last updated.

An empty result means entry-points.md and the module docs' "Public
interface" sections agree with each other. As with verify_diagram.py, that
does NOT mean either one is correct against the actual source code -- this
is a drift check between two pieces of *output*, not a re-verification
against source. If something is flagged, open the module(s) involved and
fix whichever side is stale -- don't just delete the flagged row/bullet to
make the tool quiet.

Parsing notes (heuristic, not a general-purpose parser, same caveat as
verify_diagram.py):
  - entry-points.md: reads the four standard tables (HTTP routes, CLI
    commands, Queue / event consumers, Scheduled / cron jobs) by heading,
    pulls the "Module" column (backtick-wrapped) and one identifying
    column per table (Path / Command / Topic-event / Schedule).
  - modules/*.md: scans "Public interface" bullets for patterns that look
    like an HTTP route (METHOD + path), a cron schedule (5-6 whitespace-
    separated cron fields), or queue/event language (topic/consumer/
    subscribe/publish keywords) -- CLI commands are deliberately NOT
    pattern-matched in the reverse direction (module doc -> entry-points),
    since a bare backtick token in "Public interface" is too easily
    confused with an ordinary function reference; CLI rows are still
    checked in the forward direction (entry-points.md -> module doc).
  - A collapsed row (e.g. "38 routes under /api/v1/resources/* -- ...", per
    output-templates.md's guidance for large repetitive route sets) won't
    match a literal path anywhere and will not be flagged as
    entry_points_unconfirmed for that reason alone; this script only flags
    rows whose Path/Command/Topic looks like a normal single-entry value.
"""
import argparse
import json
import re
import sys
from pathlib import Path

TABLE_HEADINGS = {
    "http_routes": re.compile(r"^#{1,6}\s*HTTP routes", re.IGNORECASE),
    "cli_commands": re.compile(r"^#{1,6}\s*CLI commands", re.IGNORECASE),
    "queue_consumers": re.compile(r"^#{1,6}\s*Queue\s*/\s*event consumers", re.IGNORECASE),
    "cron_jobs": re.compile(r"^#{1,6}\s*Scheduled\s*/\s*cron jobs", re.IGNORECASE),
}
ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
CELL_SPLIT_RE = re.compile(r"\s*\|\s*")
BACKTICK_RE = re.compile(r"`([^`]+)`")

PUBLIC_INTERFACE_RE = re.compile(r"^#{1,6}\s*Public interface", re.IGNORECASE)
HTTP_VERB_PATH_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(`?/[^\s`]*`?)", re.IGNORECASE
)
CRON_FIELD_RE = re.compile(r"`((?:[\d*/,\-]+\s+){4,5}[\d*/,\-]+)`")
QUEUE_KEYWORD_RE = re.compile(r"\b(topic|consumer|subscri\w+|publish\w*|queue)\b", re.IGNORECASE)


def parse_table(text, heading_re):
    """Return list of raw cell-lists for every data row under `heading_re`
    (skips the header row and the |---|---| separator row)."""
    rows = []
    in_section = in_table = False
    header_seen = False
    for line in text.splitlines():
        if heading_re.match(line):
            in_section = True
            header_seen = False
            in_table = False
            continue
        if in_section and ANY_HEADING_RE.match(line) and not heading_re.match(line):
            in_section = False
            continue
        if not in_section:
            continue
        m = TABLE_ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in CELL_SPLIT_RE.split(m.group(1)) if c.strip() != ""]
        if not header_seen:
            header_seen = True
            in_table = True
            continue
        if in_table and cells and set("".join(cells)) <= set("-: "):
            continue  # the |---|---| separator row
        if in_table and cells:
            rows.append(cells)
    return rows


def strip_backticks(s):
    m = BACKTICK_RE.search(s)
    return m.group(1) if m else s.strip()


def extract_entry_point_rows(text):
    """Returns list of {kind, module, detail, raw} for every data row across
    the four standard tables. `detail` is the identifying column
    (Path/Command/Topic/Schedule), backtick-stripped."""
    # column index of (module_col, detail_col) per table, 0-based, per
    # output-templates.md's fixed column order for each table
    layout = {
        "http_routes": (2, 1),      # | Method | Path | Module | Handler | File |
        "cli_commands": (1, 0),     # | Command | Module | What it does | File |
        "queue_consumers": (1, 0),  # | Topic / event | Module | Triggered by | File |
        "cron_jobs": (1, 0),        # | Schedule | Module | What it does | File |
    }
    out = []
    for kind, heading_re in TABLE_HEADINGS.items():
        mod_idx, detail_idx = layout[kind]
        for cells in parse_table(text, heading_re):
            if len(cells) <= max(mod_idx, detail_idx):
                continue
            module = strip_backticks(cells[mod_idx])
            detail = strip_backticks(cells[detail_idx])
            if not module or module in {"...", "-", "--"} or not detail or detail in {"...", "-", "--"}:
                continue
            out.append({"kind": kind, "module": module, "detail": detail, "raw": " | ".join(cells)})
    return out


def extract_public_interface_text(module_text):
    lines = []
    in_section = False
    for line in module_text.splitlines():
        if PUBLIC_INTERFACE_RE.match(line):
            in_section = True
            continue
        if in_section and ANY_HEADING_RE.match(line) and not PUBLIC_INTERFACE_RE.match(line):
            in_section = False
            continue
        if in_section:
            lines.append(line)
    return "\n".join(lines)


def find_public_interface_candidates(section_text):
    """Heuristic scan for route/cron/queue-looking bullets, deliberately
    excluding CLI commands (see module docstring)."""
    candidates = []
    for m in HTTP_VERB_PATH_RE.finditer(section_text):
        candidates.append({"kind": "http_routes", "detail": m.group(2).strip("`")})
    for m in CRON_FIELD_RE.finditer(section_text):
        candidates.append({"kind": "cron_jobs", "detail": m.group(1).strip()})
    for line in section_text.splitlines():
        if QUEUE_KEYWORD_RE.search(line):
            bt = BACKTICK_RE.findall(line)
            if bt:
                candidates.append({"kind": "queue_consumers", "detail": bt[0]})
    return candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root", help="path to docs/anatomy/ (or wherever the trace was written)")
    args = ap.parse_args()

    root = Path(args.output_root).resolve()
    ep_path = root / "entry-points.md"
    modules_dir = root / "modules"

    if not ep_path.exists():
        print(json.dumps({"error": f"not found: {ep_path}"}))
        sys.exit(1)
    if not modules_dir.is_dir():
        print(json.dumps({"error": f"not found: {modules_dir}"}))
        sys.exit(1)

    ep_text = ep_path.read_text(errors="ignore")
    ep_rows = extract_entry_point_rows(ep_text)

    module_texts = {}
    module_pi_texts = {}
    for md in sorted(modules_dir.glob("*.md")):
        slug = md.stem
        text = md.read_text(errors="ignore")
        module_texts[slug] = text
        module_pi_texts[slug] = extract_public_interface_text(text)

    # --- forward check: every entry-points.md row confirmed in its module ---
    entry_points_unconfirmed = []
    for row in ep_rows:
        slug = row["module"]
        if slug not in module_pi_texts:
            entry_points_unconfirmed.append({**row, "reason": f"no modules/{slug}.md found"})
            continue
        if row["detail"] not in module_pi_texts[slug]:
            entry_points_unconfirmed.append({**row, "reason": "detail not found in module's Public interface section"})

    # --- reverse check: candidate entry points in module docs, missing from entry-points.md ---
    public_interface_uncaptured = []
    for slug, pi_text in module_pi_texts.items():
        for cand in find_public_interface_candidates(pi_text):
            if cand["detail"] not in ep_text:
                public_interface_uncaptured.append({"module": slug, **cand})

    result = {
        "output_root": str(root),
        "modules_found": sorted(module_texts.keys()),
        "entry_point_rows_checked": len(ep_rows),
        "entry_points_unconfirmed": entry_points_unconfirmed,
        "public_interface_uncaptured": public_interface_uncaptured,
        "counts": {
            "entry_points_unconfirmed": len(entry_points_unconfirmed),
            "public_interface_uncaptured": len(public_interface_uncaptured),
        },
        "note": (
            "Empty lists mean entry-points.md and each module's Public "
            "interface section agree with each other -- this checks "
            "agreement between two pieces of output, not either one "
            "against the actual source code, which is Phase 4's job. "
            "Heuristic pattern matching, not a full parser -- see the "
            "module docstring for what's deliberately not checked (e.g. "
            "collapsed large-route-set rows, CLI commands in the reverse "
            "direction)."
        ),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()