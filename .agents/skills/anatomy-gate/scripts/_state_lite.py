"""
_state_lite.py -- vendored, stdlib-only copy of the content-hashing and
manifest-diff logic from the `anatomy` skill's `scripts/_common.py` and
`scripts/state.py` (specifically: IGNORE_DIR_NAMES, IGNORE_FILE_SUFFIXES,
is_ignored_dir, load_gitignore_patterns, walk_source_files, sha256_file,
sha256_text, hash_module, and cmd_diff's comparison logic).

Why vendored instead of imported: this skill is meant to be installable
and runnable on its own, without a hard runtime dependency on locating
another skill's install path -- which varies (/mnt/skills/public/, a
user-installed location, a different machine's skills directory
entirely). The `anatomy` skill's own scripts already accept this exact
kind of small duplication in more than one place for the same reason
(rollup.py / verify_health_signals.py both duplicate the same rollup
computation rather than import across files; graph_export.py duplicates
extract_coverage() rather than reach into rollup.py for it) -- this is
the same tradeoff, just crossing a skill boundary instead of a
within-skill file boundary.

CORRECTNESS REQUIREMENT: the file-selection logic below (which files
count toward a module's hash) MUST stay byte-for-byte identical to
anatomy/scripts/_common.py's walk_source_files, or a fresh hash computed
here will disagree with a manifest written by anatomy's own state.py for
reasons that have nothing to do with the source actually changing --
exactly the kind of false-positive/false-negative staleness result this
skill exists to avoid. There is no automated link between the two
copies; if anatomy/scripts/_common.py's IGNORE_DIR_NAMES or
IGNORE_FILE_SUFFIXES ever change, update this file by hand to match.
"""
import hashlib
import os
from pathlib import Path

IGNORE_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", "target", ".next", ".nuxt", "out",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", ".gradle", "bin", "obj", "Pods", "DerivedData",
    ".terraform", ".serverless", "egg-info", ".eggs", ".cache", ".parcel-cache",
    "site-packages", "bower_components", ".dart_tool",
}
IGNORE_FILE_SUFFIXES = {".pyc", ".pyo", ".so", ".o", ".class", ".min.js", ".min.css"}


def is_ignored_dir(name: str) -> bool:
    return name in IGNORE_DIR_NAMES or name.startswith(".") and name not in {".", ".."} and name not in {".github", ".circleci"}


def load_gitignore_patterns(repo_root: Path):
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


def hash_module(repo_root: Path, module_rel_path: str):
    """Identical to anatomy/scripts/state.py's hash_module(). Returns
    {"hash": ..., "file_count": N} or None if the module path is gone."""
    repo_root = Path(repo_root)
    module_dir = repo_root / module_rel_path
    if not module_dir.exists():
        return None
    file_hashes = []
    if module_dir.is_file():
        file_hashes.append(f"{module_rel_path}:{sha256_file(module_dir)}")
    else:
        for abs_path, _rel_to_module in walk_source_files(module_dir):
            rel = abs_path.relative_to(repo_root)
            file_hashes.append(f"{rel}:{sha256_file(abs_path)}")
        file_hashes.sort()
    combined = sha256_text("\n".join(file_hashes))
    return {"hash": combined, "file_count": len(file_hashes)}


def hash_modules(repo_root: Path, modules_map: dict) -> dict:
    """modules_map: {"slug": "relative/path", ...} (Phase 2's mapping,
    persisted as _modules.json). Returns {"slug": {"hash":.., "file_count":..}
    | {"error": "..."}}, same shape as state.py hash-modules' stdout."""
    out = {}
    for slug, rel_path in modules_map.items():
        h = hash_module(repo_root, rel_path)
        out[slug] = h if h is not None else {"error": f"path not found: {rel_path}"}
    return out


def diff_hashes(old_modules: dict, fresh_hashes: dict) -> dict:
    """old_modules: the "modules" block of a _manifest.json (slug -> {hash,
    file_count}). fresh_hashes: hash_modules()'s output. Identical
    comparison logic to state.py's cmd_diff."""
    unchanged, changed, added = [], [], []
    for slug, info in fresh_hashes.items():
        if "error" in info:
            continue
        if slug not in old_modules:
            added.append(slug)
        elif old_modules[slug].get("hash") != info.get("hash"):
            changed.append(slug)
        else:
            unchanged.append(slug)
    removed = [slug for slug in old_modules if slug not in fresh_hashes]
    total = len(unchanged) + len(changed) + len(added) + len(removed)
    change_ratio = (len(changed) + len(added) + len(removed)) / total if total else 0.0
    return {
        "unchanged": sorted(unchanged),
        "changed": sorted(changed),
        "added": sorted(added),
        "removed": sorted(removed),
        "change_ratio": round(change_ratio, 3),
    }
