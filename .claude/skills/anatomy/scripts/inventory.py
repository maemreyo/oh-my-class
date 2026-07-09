#!/usr/bin/env python3
"""
inventory.py -- structural overview of a codebase, for Phase 1 of system-trace.

Usage:
    python3 inventory.py <repo_root> [--max-depth N] [--top-n-largest N]

Prints JSON to stdout with:
  - total_files, languages (histogram)
  - manifests found (with a few parsed key fields, best-effort)
  - a bounded-depth directory tree annotated with file counts
  - top-level directories with file counts (candidate module roots)
  - the largest source files by line count (likely-central "hotspot" files,
    useful for prioritizing reading effort in big codebases)
  - any AMBIGUOUS_DIR_NAMES encountered (e.g. "packages") that Claude should
    look at directly rather than assume

This script only reads structure and small manifest files -- it never tries
to summarize what the code does. That judgment call is Claude's job, done by
actually reading the files this script points at.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    walk_source_files, detect_language, MANIFEST_FILENAMES,
    AMBIGUOUS_DIR_NAMES, is_ignored_dir, load_gitignore_patterns,
)


def parse_manifest(path: Path):
    """Best-effort extraction of a few high-signal fields. Never raises --
    worst case we just return {} and Claude reads the file directly."""
    name = path.name
    fields = {}
    try:
        if name == "package.json":
            data = json.loads(path.read_text(errors="ignore"))
            fields["name"] = data.get("name")
            fields["workspaces"] = data.get("workspaces")
            deps = list(data.get("dependencies", {}).keys())
            fields["dependencies_sample"] = deps[:15]
            fields["scripts"] = list(data.get("scripts", {}).keys())
        elif name == "pyproject.toml":
            try:
                import tomllib
                data = tomllib.loads(path.read_text(errors="ignore"))
                proj = data.get("project", {})
                fields["name"] = proj.get("name")
                fields["dependencies_sample"] = (proj.get("dependencies") or [])[:15]
                if "tool" in data and "poetry" in data["tool"]:
                    fields["name"] = fields.get("name") or data["tool"]["poetry"].get("name")
            except Exception:
                fields["note"] = "tomllib unavailable or unparsable; read file directly"
        elif name == "go.mod":
            text = path.read_text(errors="ignore")
            for line in text.splitlines():
                if line.startswith("module "):
                    fields["module"] = line.split(maxsplit=1)[1].strip()
                    break
        elif name == "Cargo.toml":
            try:
                import tomllib
                data = tomllib.loads(path.read_text(errors="ignore"))
                fields["name"] = data.get("package", {}).get("name")
                fields["workspace_members"] = data.get("workspace", {}).get("members")
            except Exception:
                pass
        elif name == "composer.json":
            data = json.loads(path.read_text(errors="ignore"))
            fields["name"] = data.get("name")
        elif name in {"pom.xml", "build.gradle", "build.gradle.kts"}:
            fields["note"] = "JVM build file -- read directly for module/dependency layout"
    except Exception as e:
        fields["parse_error"] = str(e)
    return fields


def build_tree(repo_root: Path, max_depth: int):
    """Bounded-depth directory tree with per-directory file counts.
    Deliberately coarse -- this is for orientation, not a substitute for
    reading actual files."""
    extra_ignores = load_gitignore_patterns(repo_root)

    def count_files_recursive(d: Path) -> int:
        total = 0
        try:
            for entry in d.iterdir():
                if entry.is_dir():
                    if is_ignored_dir(entry.name) or entry.name in extra_ignores:
                        continue
                    total += count_files_recursive(entry)
                elif entry.is_file():
                    total += 1
        except OSError:
            pass
        return total

    def recurse(d: Path, depth: int):
        node = {"name": d.name or str(d), "file_count": count_files_recursive(d)}
        if depth >= max_depth:
            return node
        children = []
        try:
            for entry in sorted(d.iterdir(), key=lambda p: p.name):
                if entry.is_dir():
                    if is_ignored_dir(entry.name) or entry.name in extra_ignores:
                        continue
                    children.append(recurse(entry, depth + 1))
        except OSError:
            pass
        if children:
            node["children"] = children
        return node

    return recurse(repo_root, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--top-n-largest", type=int, default=15)
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(json.dumps({"error": f"not a directory: {repo_root}"}))
        sys.exit(1)

    languages = {}
    manifests = []
    ambiguous_dirs_found = set()
    file_line_counts = []  # (rel_path, line_count)
    total_files = 0

    for abs_path, rel_path in walk_source_files(repo_root):
        total_files += 1
        for part in rel_path.parts[:-1]:
            if part in AMBIGUOUS_DIR_NAMES:
                ambiguous_dirs_found.add(part)

        lang = detect_language(abs_path)
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
            try:
                with open(abs_path, "r", errors="ignore") as fh:
                    n = sum(1 for _ in fh)
                file_line_counts.append((str(rel_path), n))
            except OSError:
                pass

        if abs_path.name in MANIFEST_FILENAMES:
            manifests.append({
                "path": str(rel_path),
                "type": abs_path.name,
                "fields": parse_manifest(abs_path),
            })

    top_level = []
    try:
        extra_ignores = load_gitignore_patterns(repo_root)
        for entry in sorted(repo_root.iterdir(), key=lambda p: p.name):
            if entry.is_dir():
                if is_ignored_dir(entry.name) or entry.name in extra_ignores:
                    continue
                fc = sum(1 for _ in walk_source_files(entry))
                top_level.append({"name": entry.name, "type": "dir", "file_count": fc})
            elif entry.is_file():
                top_level.append({"name": entry.name, "type": "file"})
    except OSError:
        pass

    file_line_counts.sort(key=lambda t: t[1], reverse=True)
    hotspots = [{"path": p, "lines": n} for p, n in file_line_counts[: args.top_n_largest]]

    result = {
        "repo_root": str(repo_root),
        "total_files_scanned": total_files,
        "languages": dict(sorted(languages.items(), key=lambda kv: kv[1], reverse=True)),
        "manifests": manifests,
        "top_level": top_level,
        "ambiguous_dirs_found": sorted(ambiguous_dirs_found),
        "largest_files_by_line_count": hotspots,
        "directory_tree": build_tree(repo_root, args.max_depth),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
