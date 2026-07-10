#!/usr/bin/env python3
"""
freshness_check.py -- lightweight freshness check for a specific module (or
the whole repo) in an existing docs/anatomy/ output, for the anatomy-ask
skill's fast-path answers.

Usage:
    python3 freshness_check.py <output_root> [--repo-root PATH] [--module SLUG]

<output_root> is docs/anatomy/ (or wherever a prior `anatomy` run wrote its
output). This is the exact same hash-modules + diff computation
`anatomy`'s own SKILL.md Phase 0 "Fast path" section describes -- this
script just makes it a one-shot, self-contained call for a skill that
never loads the rest of anatomy's 7-Phase workflow.

Without --module: prints the same shape as anatomy/scripts/state.py's
`diff` subcommand (unchanged/changed/added/removed/change_ratio).

With --module <slug>: prints that plus a `module_status` field
(one of "unchanged", "changed", "added", "not_found") and a ready-to-use
`caveat` string -- empty if the module is unchanged (repo-wide or not),
non-empty if the module itself is stale/missing, meant to be prepended
to an answer built from that module's existing doc rather than making the
caller re-derive the wording each time.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _state_lite import diff_hashes, hash_modules  # noqa: E402


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_root", help="path to docs/anatomy/ (or wherever the trace was written)")
    ap.add_argument("--repo-root", default=None, help="repo root to hash against (default: cwd)")
    ap.add_argument("--module", default=None, help="a specific module slug to report freshness for")
    args = ap.parse_args()

    output_root = Path(args.output_root).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()

    manifest_path = output_root / "_manifest.json"
    modules_path = output_root / "_modules.json"

    if not manifest_path.is_file():
        print(json.dumps({
            "status": "error",
            "message": f"no _manifest.json found at {manifest_path} -- run the anatomy skill first, there's nothing to answer from yet",
        }, indent=2))
        sys.exit(2)

    if not modules_path.is_file():
        print(json.dumps({
            "status": "error",
            "message": (
                f"no _modules.json found at {modules_path} -- this output predates that file; "
                "freshness can't be checked per-module. Either re-run anatomy to refresh it, "
                "or answer with an explicit 'freshness unverified' caveat."
            ),
        }, indent=2))
        sys.exit(2)

    old_manifest = load_json(manifest_path)
    modules_map = load_json(modules_path)
    if old_manifest is None or modules_map is None:
        print(json.dumps({"status": "error", "message": "_manifest.json or _modules.json couldn't be parsed"}, indent=2))
        sys.exit(2)

    fresh_hashes = hash_modules(repo_root, modules_map)
    diff = diff_hashes(old_manifest.get("modules", {}), fresh_hashes)

    result = {
        "status": "ok",
        "output_root": str(output_root),
        "generated_at": old_manifest.get("generated_at"),
        "source_commit_at_last_trace": old_manifest.get("source_commit"),
        **diff,
    }

    if args.module:
        slug = args.module
        if slug in diff["unchanged"]:
            module_status, caveat = "unchanged", ""
        elif slug in diff["changed"]:
            module_status = "changed"
            caveat = (
                f"Heads up: `{slug}`'s source has changed since this trace was last run "
                f"(generated {old_manifest.get('generated_at', 'at an unknown time')})"
                + (f", commit {old_manifest['source_commit']}" if old_manifest.get("source_commit") else "")
                + " -- the module doc below may no longer be fully accurate."
            )
        elif slug in diff["added"]:
            module_status = "added"
            caveat = f"`{slug}` exists in source but has no traced documentation yet (added since the last anatomy run)."
        elif slug in diff["removed"]:
            module_status = "removed"
            caveat = f"`{slug}` has a doc in docs/anatomy/modules/, but its source directory no longer exists -- treat the doc as historical, not current."
        else:
            module_status = "not_found"
            caveat = f"`{slug}` isn't a known module slug in this trace -- check index.md's module table for the right one."
        result["module"] = slug
        result["module_status"] = module_status
        result["caveat"] = caveat
        if diff["change_ratio"] > 0 and module_status == "unchanged":
            result["caveat"] = (
                f"Other modules have changed since this trace, but `{slug}` itself hasn't -- this answer is current."
            )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
