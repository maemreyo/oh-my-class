#!/usr/bin/env python3
"""
state.py -- manifest read/hash/diff/write, for Phase 0 and Phase 6 of the
anatomy skill's tracing workflow (handling a pre-existing docs/anatomy
output folder, including one left over at the older default location,
docs/system-trace, by a previous version of this skill).

Subcommands:
  hash-modules <repo_root> <modules.json>
      modules.json: {"module-slug": "relative/path/to/module", ...}
      Prints JSON: {"module-slug": {"hash": "...", "file_count": N}, ...}
      Hash is content-based (sha256 over sorted relative file paths + each
      file's sha256), so it is immune to touch-without-change mtime noise
      and works identically whether or not the repo uses git. Files under
      noise directories nested inside the module (node_modules,
      __pycache__, dist, .venv, etc. -- the same list walk_source_files
      prunes everywhere else) are excluded from the hash, so a rebuild or a
      dependency install doesn't masquerade as a source change.

  diff <old_manifest.json> <fresh_hashes.json>
      Compares a previous manifest's per-module hashes against a freshly
      computed hash-modules result. Prints JSON:
      {"unchanged": [...], "changed": [...], "added": [...], "removed": [...],
       "change_ratio": 0.0-1.0}

  write <manifest_path> <data.json>
      Writes/overwrites the manifest file with the given data (adds
      "generated_at" and "source_commit" automatically).

  git-commit <repo_root>
      Prints the current HEAD commit hash, or null if not a git repo / no
      commits yet. Convenience used when writing a fresh manifest.

Why content hashing instead of only git diff: many real invocations happen
against a working tree with uncommitted changes, or against a codebase that
isn't a git repo at all (vendored code drop, extracted archive, etc). Content
hashing works in every case; git commit info is recorded only as a friendly
extra data point, never as the sole source of truth for "did this change".
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import sha256_file, sha256_text, walk_source_files  # noqa: E402


def hash_module(repo_root: Path, module_rel_path: str):
    module_dir = repo_root / module_rel_path
    if not module_dir.exists():
        return None
    file_hashes = []
    if module_dir.is_file():
        file_hashes.append(f"{module_rel_path}:{sha256_file(module_dir)}")
    else:
        # Reuse walk_source_files' noise-dir pruning (node_modules,
        # __pycache__, dist, .venv, etc.) instead of a raw rglob. A module
        # directory very commonly contains its own build/dependency
        # artifacts nested inside it (a workspace package's own
        # node_modules, a Python package's __pycache__, a built dist/) --
        # hashing those would make "content changed" noisy and untrustworthy
        # (a bare `npm install` or `pip install -e .` could flip the hash
        # with zero source change) and would be needlessly slow on top of
        # that. walk_source_files(module_dir) yields paths relative to
        # module_dir; re-derive the repo-root-relative path for each so the
        # hash key stays identical to before this fix, keeping old manifests
        # comparable against fresh hashes computed with this version.
        for abs_path, _rel_to_module in walk_source_files(module_dir):
            rel = abs_path.relative_to(repo_root)
            file_hashes.append(f"{rel}:{sha256_file(abs_path)}")
        file_hashes.sort()
    combined = sha256_text("\n".join(file_hashes))
    return {"hash": combined, "file_count": len(file_hashes)}


def cmd_hash_modules(args):
    repo_root = Path(args.repo_root).resolve()
    modules = json.loads(Path(args.modules_json).read_text())
    out = {}
    for slug, rel_path in modules.items():
        h = hash_module(repo_root, rel_path)
        if h is None:
            out[slug] = {"error": f"path not found: {rel_path}"}
        else:
            out[slug] = h
    print(json.dumps(out, indent=2))


def cmd_diff(args):
    old_manifest = json.loads(Path(args.old_manifest).read_text())
    fresh = json.loads(Path(args.fresh_hashes).read_text())

    old_modules = old_manifest.get("modules", {})
    unchanged, changed, added = [], [], []

    for slug, info in fresh.items():
        if "error" in info:
            continue
        if slug not in old_modules:
            added.append(slug)
        elif old_modules[slug].get("hash") != info.get("hash"):
            changed.append(slug)
        else:
            unchanged.append(slug)

    removed = [slug for slug in old_modules if slug not in fresh]

    total = len(unchanged) + len(changed) + len(added) + len(removed)
    change_ratio = (len(changed) + len(added) + len(removed)) / total if total else 0.0

    print(json.dumps({
        "unchanged": unchanged,
        "changed": changed,
        "added": added,
        "removed": removed,
        "change_ratio": round(change_ratio, 3),
        "recommendation": (
            "incremental update looks safe"
            if change_ratio < 0.6
            else "more than ~60% of modules differ -- consider a full re-trace "
                 "instead of patching incrementally, and confirm with the user"
        ),
    }, indent=2))


def cmd_write(args):
    data = json.loads(Path(args.data_json).read_text())
    data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    Path(args.manifest_path).write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"written": args.manifest_path}))


def cmd_git_commit(args):
    repo_root = Path(args.repo_root).resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        commit = out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        commit = None
    print(json.dumps({"commit": commit}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("hash-modules")
    p1.add_argument("repo_root")
    p1.add_argument("modules_json")
    p1.set_defaults(func=cmd_hash_modules)

    p2 = sub.add_parser("diff")
    p2.add_argument("old_manifest")
    p2.add_argument("fresh_hashes")
    p2.set_defaults(func=cmd_diff)

    p3 = sub.add_parser("write")
    p3.add_argument("manifest_path")
    p3.add_argument("data_json")
    p3.set_defaults(func=cmd_write)

    p4 = sub.add_parser("git-commit")
    p4.add_argument("repo_root")
    p4.set_defaults(func=cmd_git_commit)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
