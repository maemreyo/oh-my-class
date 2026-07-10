#!/usr/bin/env python3
"""
docs_gate.py -- pass/fail docs-staleness gate over an existing docs/anatomy/
output, for use in a pre-commit hook or a CI check on a pull request.

Usage:
    python3 docs_gate.py <output_root> [--repo-root PATH]
                          [--fail-on {high,medium,low,none}]
                          [--format {json,text}]

<output_root> is docs/anatomy/ (or wherever a prior anatomy run wrote its
output) -- the folder containing _manifest.json, _modules.json, and
optionally _graph.json. --repo-root defaults to the current working
directory, which is correct for the common case of running this from a
pre-commit hook or a CI job checked out at the repo root; pass it
explicitly if this is invoked from somewhere else.

What this does, and why it's a separate skill from `anatomy` itself:
`anatomy`'s own Phase 0 already computes a hash-modules + diff for its own
purposes (deciding whether a re-trace can run incrementally, or whether a
narrow question can be answered from existing docs without a run at all).
Neither of those is "block an action until docs are refreshed" -- that
needs a hard pass/fail result with an exit code, not a paragraph for a
human to read, and it needs to run without loading anatomy's full 7-Phase
workflow into context just to answer "is anything stale." This script is
that: it re-runs the same hash-modules + diff computation as a lightweight,
self-contained check, then goes one step further anatomy's own diff
doesn't: it cross-references which modules are stale against
_graph.json's `health_signals` (written by anatomy's graph_export.py) to
rank severity, so a gate running on every commit surfaces a stale
central/most-connected module loudly and a stale, already-orphaned module
quietly -- rather than an undifferentiated wall of red that trains people
to ignore it.

Severity policy:
  - removed module (docs describe a module whose source directory is
    gone): always "high" -- actively misleading, not just outdated.
  - added module (source exists, no manifest entry for it yet): always
    "high" -- there's no doc coverage for it at all yet.
  - changed module (source hash no longer matches the manifest):
      - "high"   if the module appears in _graph.json's
                 health_signals.most_connected (its docs -- and everything
                 that cites it in a "Depends on"/"Used by" line -- are the
                 most likely to actually mislead someone reading them)
      - "low"    if the module appears in orphan_candidates (nothing else
                 in the traced graph depends on its documented interface,
                 so stale docs here have the smallest blast radius)
      - "medium" otherwise, or for every changed module if _graph.json
                 isn't present/readable (health-signal-based prioritization
                 unavailable -- see the `graph_unavailable` note in output)

This mirrors, deliberately, the pass/fail JSON + exit-code shape of
anatomy's own verify_diagram.py / verify_entry_points.py /
verify_health_signals.py, not the narrative style of SKILL.md prose --
this script is meant to be read by a hook/CI runner as much as by a human.

Content-hash granularity is intentionally left coarse, same as
anatomy/scripts/state.py: a comment-only or whitespace-only change still
counts as "changed." Filtering that out risks false negatives (docs that
actually did drift, silently excused) in exchange for avoiding false
positives (a nag for a no-op change) -- the wrong side of that trade for a
gate whose whole job is catching drift, so no such filtering is applied
here either.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _state_lite import diff_hashes, hash_modules  # noqa: E402

SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


def git_head(repo_root: Path):
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def classify(diff, graph):
    """Returns (findings, graph_unavailable: bool)."""
    findings = []
    graph_unavailable = graph is None

    for slug in diff["removed"]:
        findings.append({
            "module": slug,
            "status": "removed",
            "severity": "high",
            "reason": (
                "source directory for this module no longer exists, but the "
                "manifest still has an entry for it -- modules/<slug>.md may "
                "still be sitting there describing code that's gone"
            ),
        })

    for slug in diff["added"]:
        findings.append({
            "module": slug,
            "status": "added",
            "severity": "high",
            "reason": (
                "source exists but has no prior manifest entry -- likely "
                "undocumented until the next anatomy run"
            ),
        })

    most_connected = {}
    orphans = set()
    if graph:
        hs = graph.get("health_signals", {})
        for rank, row in enumerate(hs.get("most_connected", []), start=1):
            most_connected[row.get("module")] = {"rank": rank, "total_degree": row.get("total_degree")}
        orphans = set(hs.get("orphan_candidates", []))

    for slug in diff["changed"]:
        if graph_unavailable:
            findings.append({
                "module": slug, "status": "changed", "severity": "medium",
                "reason": (
                    "_graph.json not found or unreadable -- health-signal-based "
                    "prioritization unavailable, defaulting every changed module to medium"
                ),
            })
        elif slug in most_connected:
            mc = most_connected[slug]
            findings.append({
                "module": slug, "status": "changed", "severity": "high",
                "reason": (
                    f"source changed since last trace and this module ranks "
                    f"#{mc['rank']} in most_connected (degree {mc['total_degree']}) -- "
                    f"its docs, and every module citing it in a Depends on/Used by "
                    f"line, are the most likely to now be wrong"
                ),
            })
        elif slug in orphans:
            findings.append({
                "module": slug, "status": "changed", "severity": "low",
                "reason": "source changed since last trace; module was an orphan candidate (no confirmed internal edges), so blast radius of stale docs here is small",
            })
        else:
            findings.append({
                "module": slug, "status": "changed", "severity": "medium",
                "reason": "source changed since last trace; not currently flagged as most-connected or orphaned",
            })

    return findings, graph_unavailable


def format_text(result):
    lines = []
    status_word = "PASS" if result["status"] == "pass" else "FAIL"
    lines.append(f"docs-staleness gate: {status_word}  (output_root={result['output_root']})")
    if result.get("graph_unavailable"):
        lines.append("  note: _graph.json not found -- severity ranking degraded to medium-only")
    if not result["findings"]:
        lines.append("  nothing stale -- docs/anatomy is current")
    else:
        order = {"high": 0, "medium": 1, "low": 2}
        for f in sorted(result["findings"], key=lambda f: order[f["severity"]]):
            lines.append(f"  [{f['severity'].upper():6}] {f['module']} ({f['status']}) -- {f['reason']}")
    lines.append(f"  change_ratio={result['change_ratio']}  fail_on={result['fail_on']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root", help="path to docs/anatomy/ (or wherever the trace was written)")
    ap.add_argument("--repo-root", default=None, help="repo root to hash against (default: cwd)")
    ap.add_argument("--fail-on", choices=["high", "medium", "low", "none"], default="high",
                     help="minimum severity that causes a non-zero exit (default: high). "
                          "'none' means report-only -- always exit 0.")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args()

    output_root = Path(args.output_root).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()

    manifest_path = output_root / "_manifest.json"
    modules_path = output_root / "_modules.json"
    graph_path = output_root / "_graph.json"

    if not manifest_path.is_file():
        print(json.dumps({
            "status": "error",
            "message": f"no _manifest.json found at {manifest_path} -- run the anatomy skill first",
        }, indent=2))
        sys.exit(2)

    if not modules_path.is_file():
        print(json.dumps({
            "status": "error",
            "message": (
                f"no _modules.json found at {modules_path} -- this output predates that file "
                "(older anatomy version) or is otherwise incomplete; re-run anatomy to refresh it"
            ),
        }, indent=2))
        sys.exit(2)

    old_manifest = load_json(manifest_path)
    modules_map = load_json(modules_path)
    if old_manifest is None or modules_map is None:
        print(json.dumps({
            "status": "error",
            "message": "_manifest.json or _modules.json exists but couldn't be parsed as JSON",
        }, indent=2))
        sys.exit(2)

    fresh_hashes = hash_modules(repo_root, modules_map)
    diff = diff_hashes(old_manifest.get("modules", {}), fresh_hashes)

    graph = load_json(graph_path) if graph_path.is_file() else None
    findings, graph_unavailable = classify(diff, graph)

    if args.fail_on == "none":
        fails = False
    else:
        threshold = SEVERITY_RANK[args.fail_on]
        fails = any(SEVERITY_RANK[f["severity"]] >= threshold for f in findings)

    result = {
        "status": "fail" if fails else "pass",
        "output_root": str(output_root),
        "repo_root": str(repo_root),
        "source_commit_at_last_trace": old_manifest.get("source_commit"),
        "current_commit": git_head(repo_root),
        "change_ratio": diff["change_ratio"],
        "unchanged_count": len(diff["unchanged"]),
        "findings": findings,
        "graph_unavailable": graph_unavailable,
        "fail_on": args.fail_on,
        "note": (
            "Content-hash diff is coarse -- a comment/whitespace-only edit still counts as "
            "'changed'. Severity comes from cross-referencing changed/added/removed modules "
            "against _graph.json's health_signals, not from re-reading source. An empty "
            "findings list means every module's docs are still hashed-consistent with source; "
            "it does not re-verify that the docs were ever accurate to begin with."
        ),
    }

    if args.format == "text":
        print(format_text(result))
    else:
        print(json.dumps(result, indent=2))

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
