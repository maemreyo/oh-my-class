"""
Shared helpers for the anatomy skill's scripts.
No third-party dependencies -- stdlib only, so this runs anywhere Python 3.8+ runs.
"""
import hashlib
import json
import os
from pathlib import Path

# Directories that are never source-of-truth for architecture: build output,
# dependency caches, VCS internals. Matched by exact directory name at any depth.
IGNORE_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", "target", ".next", ".nuxt", "out",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", ".gradle", "bin", "obj", "Pods", "DerivedData",
    ".terraform", ".serverless", "egg-info", ".eggs", ".cache", ".parcel-cache",
    "site-packages", "bower_components", ".dart_tool",
}
# "packages" and "vendor" are deliberately NOT in IGNORE_DIR_NAMES, even
# though they're common noise-dir names, because they're ambiguous: real
# first-party module dir in some monorepos (pnpm/Lerna/Nx/Turborepo all use
# "packages/*" as their canonical workspace-member convention), vendored
# third-party deps in others (Go, PHP/Composer both use "vendor/" for real
# dependency snapshots). Pruning them outright would silently skip actual
# application code for the former case. Instead they're walked normally and
# flagged via AMBIGUOUS_DIR_NAMES below, so inventory.py's
# ambiguous_dirs_found lets Claude look at a sample file and decide per
# module-detection.md, rather than either interpretation being assumed
# silently. Keep these out of IGNORE_DIR_NAMES: walk_source_files prunes
# before the ambiguous-dir check ever sees a file inside, so if either name
# ends up back in IGNORE_DIR_NAMES, ambiguous_dirs_found can never fire for
# it and this comment's premise silently stops being true.
AMBIGUOUS_DIR_NAMES = {"packages", "vendor", "third_party", "external"}

IGNORE_FILE_SUFFIXES = {".pyc", ".pyo", ".so", ".o", ".class", ".min.js", ".min.css"}

LANGUAGE_BY_EXT = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".c": "C", ".h": "C/C++ header",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".scala": "Scala",
    ".ex": "Elixir", ".exs": "Elixir",
    ".dart": "Dart",
    ".sql": "SQL",
    ".sh": "Shell", ".bash": "Shell",
    ".vue": "Vue",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
}

# Files whose presence is a strong signal about project shape / module roots.
MANIFEST_FILENAMES = {
    "package.json", "pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile",
    "poetry.lock",
    "go.mod", "go.work",
    "Cargo.toml",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "composer.json", "Gemfile", "mix.exs",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", ".env.example",
}


def is_ignored_dir(name: str) -> bool:
    return name in IGNORE_DIR_NAMES or name.startswith(".") and name not in {".", ".."} and name not in {".github", ".circleci"}


def load_gitignore_patterns(repo_root: Path):
    """Best-effort .gitignore reader. Not a full parser -- just handles plain
    directory/file name lines and simple trailing-slash dir markers, which
    covers the overwhelming majority of real .gitignore files. Good enough to
    reduce noise; not required to be perfect since IGNORE_DIR_NAMES already
    covers the common cases."""
    patterns = set()
    gi = repo_root / ".gitignore"
    if gi.exists():
        try:
            for line in gi.read_text(errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "*" in line or "/" in line:
                    continue
                patterns.add(line.rstrip("/"))
        except OSError:
            pass
    return patterns


def walk_source_files(repo_root: Path):
    """Yield (Path, rel_path) for every file worth looking at, pruning noise
    directories in-place so os.walk doesn't descend into them at all."""
    repo_root = Path(repo_root).resolve()
    extra_ignores = load_gitignore_patterns(repo_root)
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = sorted(
            d for d in dirnames
            if not is_ignored_dir(d) and d not in extra_ignores
        )
        for f in sorted(filenames):
            if any(f.endswith(suf) for suf in IGNORE_FILE_SUFFIXES):
                continue
            p = Path(dirpath) / f
            try:
                rel = p.relative_to(repo_root)
            except ValueError:
                continue
            yield p, rel


def detect_language(path: Path):
    return LANGUAGE_BY_EXT.get(path.suffix.lower())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return "unreadable"
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def slugify(name: str) -> str:
    out = []
    for ch in name.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {"-", "_", "/", " "}:
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "module"


def load_module_map(modules_json_path):
    """Load a Phase-2 `modules.json` (slug -> relative-path) and return it
    sorted longest-path-first, ready for prefix matching via
    `resolve_module_for_path`. Returns None (not {}) if the path is falsy,
    so callers can tell "no --modules flag given" apart from "an empty
    mapping was given" -- the two should behave differently (fall back to
    directory-guessing vs. genuinely finding no module for anything)."""
    if not modules_json_path:
        return None
    data = json.loads(Path(modules_json_path).read_text())
    entries = []
    for slug, rel in data.items():
        parts = tuple(p for p in Path(rel).parts if p not in (".",))
        entries.append((parts, slug))
    # Longest prefix (most path segments) first, so a nested module wins
    # over an ancestor one if both happen to be declared.
    entries.sort(key=lambda e: -len(e[0]))
    return entries


def resolve_module_for_path(rel_path_parts, module_map):
    """Longest-prefix match of a file's path parts against a loaded
    `module_map` (from `load_module_map`). Returns the owning slug, or None
    if the path doesn't fall under any declared module (e.g. a repo-root
    config file, or a directory Phase 2 didn't map) -- callers should treat
    None as 'unmapped', not silently bucket it somewhere misleading."""
    if module_map is None:
        return None
    for prefix_parts, slug in module_map:
        if rel_path_parts[: len(prefix_parts)] == prefix_parts:
            return slug
    return None


def resolve_relative_import(source_rel_path, target: str):
    """Resolve a relative-looking import target (starts with '.' or '..',
    the common JS/TS/Python-relative convention) against the importing
    file's own directory, returning a repo-root-relative path string (no
    guarantee the file exists at that exact path -- extension/index
    resolution isn't attempted, this is still a hypothesis). Returns None
    if `target` doesn't look like a relative import, so callers can fall
    back to their existing dotted/bare-package handling for everything
    else."""
    if not (target.startswith(".") or target.startswith("./") or target.startswith("../")):
        return None
    source_dir = Path(source_rel_path).parent
    combined = (source_dir / target).as_posix()
    normalized = os.path.normpath(combined).replace("\\", "/")
    if normalized.startswith(".."):
        return None  # escapes repo root -- not a resolvable in-repo target
    return normalized