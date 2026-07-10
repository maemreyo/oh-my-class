#!/usr/bin/env python3
"""
inventory.py -- structural overview of a codebase, for Phase 1 of the
anatomy skill's tracing workflow.

Usage:
    python3 inventory.py <repo_root> [--max-depth N] [--top-n-largest N]

Prints JSON to stdout with:
  - total_files, languages (histogram)
  - manifests found (with a few parsed key fields, best-effort -- including
    docker-compose.yml/.yaml services/ports/depends_on, which feeds
    deployment.md)
  - ci_config: best-effort parse of .github/workflows/*.yml and
    .circleci/config.yml -- the actual run commands CI executes, which is
    stronger ground truth for index.md's "How to build/test" line than a
    package.json script name or a README's claimed command, since it's
    what the project's own pipeline actually runs on every push. Falls
    back to package.json/Makefile-derived commands when no CI config is
    found (see the field's own "note" when empty).
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
import re
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
        elif name in {"docker-compose.yml", "docker-compose.yaml"}:
            # Structured parsing needs a real YAML parser, which breaks the
            # stdlib-only/no-installs guarantee the rest of this script
            # keeps -- so this is opportunistic: use PyYAML if it happens to
            # already be installed, and fall back to a plain note (never
            # raise) if it isn't. Either way Claude can read the file
            # directly; this just saves that step when it's available.
            try:
                import yaml
                data = yaml.safe_load(path.read_text(errors="ignore")) or {}
                services = data.get("services", {}) or {}
                summary = {}
                for svc_name, svc in services.items():
                    if not isinstance(svc, dict):
                        continue
                    depends_on = svc.get("depends_on")
                    if isinstance(depends_on, dict):
                        depends_on = list(depends_on.keys())
                    summary[svc_name] = {
                        "image": svc.get("image"),
                        "build": bool(svc.get("build")),
                        "ports": svc.get("ports", []),
                        "depends_on": depends_on or [],
                    }
                fields["services"] = summary
            except ImportError:
                fields["note"] = ("PyYAML not available in this environment -- "
                                   "read this file directly for services/ports/depends_on")
            except Exception as e:
                fields["note"] = "could not parse compose file structurally; read it directly"
                fields["parse_error"] = str(e)
    except Exception as e:
        fields["parse_error"] = str(e)
    return fields


CI_KEYWORD_BUCKETS = {
    "test": re.compile(r"\btest\w*\b", re.IGNORECASE),
    "build": re.compile(r"\bbuild\w*\b", re.IGNORECASE),
    "lint": re.compile(r"\blint\w*\b", re.IGNORECASE),
    "deploy": re.compile(r"\bdeploy\w*\b", re.IGNORECASE),
}
RUN_LINE_RE = re.compile(r"^\s*(?:-\s*)?run:\s*(.+)$")
COMMAND_LINE_RE = re.compile(r"^\s*command:\s*(.+)$")
NAME_LINE_RE = re.compile(r"^\s*(?:-\s*)?name:\s*(.+)$")


def _bucket_command(cmd: str):
    return sorted(bucket for bucket, pat in CI_KEYWORD_BUCKETS.items() if pat.search(cmd))


def _extract_run_commands_via_yaml(data):
    """Walk an already-parsed CI YAML structure (GitHub Actions or CircleCI
    shape -- both nest 'jobs' -> steps with 'run') and pull out every step's
    run command plus the nearest job/step name, without assuming which of
    the two schemas it is (they're similar enough for a generic walk)."""
    commands = []

    def walk(node, job_name=None):
        if isinstance(node, dict):
            if "jobs" in node and isinstance(node["jobs"], dict):
                for jname, jbody in node["jobs"].items():
                    walk(jbody, job_name=jname)
                return
            steps = node.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    run = step.get("run")
                    step_name = step.get("name")
                    if isinstance(run, str):
                        commands.append({
                            "job": job_name, "step": step_name,
                            "command": run.strip(),
                            "keywords": _bucket_command((step_name or "") + " " + run),
                        })
                    elif isinstance(run, dict) and isinstance(run.get("command"), str):
                        # CircleCI's `run: {command: ..., name: ...}` form
                        cmd = run["command"].strip()
                        commands.append({
                            "job": job_name, "step": run.get("name") or step_name,
                            "command": cmd,
                            "keywords": _bucket_command((run.get("name") or step_name or "") + " " + cmd),
                        })
            # CircleCI-style `commands:`/`workflows:` blocks aren't build/test
            # signal by themselves -- not walked further here, since `jobs`
            # already covers where run commands actually live.
        return

    walk(data)
    return commands


def _extract_run_commands_via_regex(text: str):
    """Fallback when PyYAML isn't installed: a line-based scan that's far
    cruder than a real parser (no nesting awareness, so `job`/`step` context
    can be wrong or absent) but still surfaces the actual run-command
    strings, which is the part that matters most for 'how to build/test'."""
    commands = []
    current_name = None
    for line in text.splitlines():
        nm = NAME_LINE_RE.match(line)
        if nm:
            current_name = nm.group(1).strip().strip("'\"")
            continue
        rm = RUN_LINE_RE.match(line)
        if rm:
            cmd = rm.group(1).strip().strip("'\"")
            if cmd and cmd != "|" and cmd != ">":
                commands.append({
                    "job": None, "step": current_name, "command": cmd,
                    "keywords": _bucket_command((current_name or "") + " " + cmd),
                })
            continue
        # CircleCI's block-mapping form: `- run:` on its own line, then
        # `name:`/`command:` as separate following keys rather than
        # `run: <command>` on one line -- RUN_LINE_RE alone misses this.
        cm = COMMAND_LINE_RE.match(line)
        if cm:
            cmd = cm.group(1).strip().strip("'\"")
            if cmd and cmd != "|" and cmd != ">":
                commands.append({
                    "job": None, "step": current_name, "command": cmd,
                    "keywords": _bucket_command((current_name or "") + " " + cmd),
                })
    return commands


def parse_ci_workflow_file(path: Path):
    text = path.read_text(errors="ignore")
    try:
        import yaml
        data = yaml.safe_load(text)
        commands = _extract_run_commands_via_yaml(data) if isinstance(data, dict) else []
        parse_method = "yaml"
        if not commands:
            # yaml parsed fine but the generic jobs/steps walk found nothing
            # (unusual schema) -- fall back to the regex scan rather than
            # reporting an empty file.
            commands = _extract_run_commands_via_regex(text)
            parse_method = "regex_fallback"
    except ImportError:
        commands = _extract_run_commands_via_regex(text)
        parse_method = "regex_no_pyyaml"
    except Exception:
        commands = _extract_run_commands_via_regex(text)
        parse_method = "regex_after_yaml_error"
    return {"parse_method": parse_method, "run_commands": commands}


def parse_ci_config(repo_root: Path):
    """Best-effort ground truth for 'how to build/test' -- CI config is what
    actually runs in practice, which is a more reliable source than guessing
    from package.json 'scripts' names or a README's claimed commands (both
    of which can drift the same way any other doc can). Looks at
    .github/workflows/*.yml(.yaml) and .circleci/config.yml(.yaml) only --
    other CI providers (GitLab CI, Jenkins, Travis, Buildkite) aren't parsed
    here; if none of the above are found but the project clearly has other
    CI config, Claude should read that file directly instead."""
    workflows = []

    gh_dir = repo_root / ".github" / "workflows"
    if gh_dir.is_dir():
        for f in sorted(gh_dir.glob("*.yml")) + sorted(gh_dir.glob("*.yaml")):
            try:
                parsed = parse_ci_workflow_file(f)
                workflows.append({
                    "provider": "github_actions",
                    "path": str(f.relative_to(repo_root)),
                    **parsed,
                })
            except OSError:
                continue

    for name in ("config.yml", "config.yaml"):
        cc = repo_root / ".circleci" / name
        if cc.exists():
            try:
                parsed = parse_ci_workflow_file(cc)
                workflows.append({
                    "provider": "circleci",
                    "path": str(cc.relative_to(repo_root)),
                    **parsed,
                })
            except OSError:
                continue
            break

    return {
        "found": bool(workflows),
        "workflows": workflows,
        "note": (
            "Only GitHub Actions (.github/workflows/*) and CircleCI "
            "(.circleci/config.yml) are parsed here. Each run_command's "
            "'keywords' field flags likely test/build/lint/deploy commands "
            "by simple keyword match on the step name and command text -- "
            "a hint for prioritization, not a guarantee. Prefer these "
            "commands over package.json 'scripts' or README claims for "
            "index.md's 'How to build/test' line when CI config exists and "
            "actually runs them; a script that's declared but never "
            "invoked by CI is weaker evidence of 'how this project is "
            "really built/tested' than one CI runs on every push."
        ) if workflows else (
            "No .github/workflows/*.yml or .circleci/config.yml found. "
            "Fall back to package.json 'scripts', Makefile targets, or "
            "other manifest-declared commands for 'How to build/test', and "
            "say in index.md that this is inferred rather than CI-verified."
        ),
    }


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
        "ci_config": parse_ci_config(repo_root),
        "top_level": top_level,
        "ambiguous_dirs_found": sorted(ambiguous_dirs_found),
        "largest_files_by_line_count": hotspots,
        "directory_tree": build_tree(repo_root, args.max_depth),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()