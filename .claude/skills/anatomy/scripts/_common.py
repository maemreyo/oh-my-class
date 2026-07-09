"""
Shared helpers for the system-trace skill's scripts.
No third-party dependencies -- stdlib only, so this runs anywhere Python 3.8+ runs.
"""
import hashlib
import os
from pathlib import Path

# Directories that are never source-of-truth for architecture: build output,
# dependency caches, VCS internals. Matched by exact directory name at any depth.
IGNORE_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", "target", "vendor", ".next", ".nuxt", "out",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", ".gradle", "bin", "obj", "Pods", "DerivedData",
    ".terraform", ".serverless", "egg-info", ".eggs", ".cache", ".parcel-cache",
    "site-packages", "bower_components", "packages", ".dart_tool",
}
# Note: "packages" is ambiguous (real module dir in some monorepos, vendored
# deps in others) -- inventory.py flags it for a human/Claude decision rather
# than silently trusting either interpretation. See module-detection.md.
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
