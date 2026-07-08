"""Config-drift lint: env vars referenced in code vs documented in .env.example.

Two sources of "referenced in code":
  - os.environ.get("X") / os.getenv("X") calls
  - pydantic_settings.BaseSettings subclasses: env_prefix + field name
    (e.g. env_prefix="MAX_TOKENS_" + field `content_creator` -> MAX_TOKENS_CONTENT_CREATOR)

Two directions checked against .env.example:
  - code -> .env.example: HARD FAIL. Code reads a var nobody documented.
  - .env.example -> code: WARN only. Some entries are intentionally
    aspirational/infra-only (e.g. docker-compose-only vars like POSTGRES_HOST).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("packages", "services")
ENV_EXAMPLE = ROOT / ".env.example"

_OS_ENV_RE = re.compile(r"os\.(?:environ\.get|getenv)\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']")
_ENV_PREFIX_RE = re.compile(r"env_prefix\s*=\s*[\"']([A-Z0-9_]*)[\"']")
_CLASS_RE = re.compile(r"^class\s+\w+\(([^)]*)\)\s*:")
_FIELD_RE = re.compile(r"^(\w+)\s*:\s*")
_ENV_EXAMPLE_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)=")


def _iter_source_files() -> list[Path]:
    files = []
    for d in SCAN_DIRS:
        for path in (ROOT / d).rglob("*.py"):
            posix = path.as_posix()
            if "/tests/" in posix or path.name.startswith("test_") or path.name.endswith("_test.py"):
                continue
            files.append(path)
    return files


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _settings_vars(text: str) -> set[str]:
    """Reconstruct FOO_BAR vars from BaseSettings subclasses in one file's source."""
    lines = text.splitlines()
    found: set[str] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _CLASS_RE.match(line)
        if not (m and "BaseSettings" in m.group(1)):
            i += 1
            continue
        class_indent = _indent(line)
        body: list[str] = []
        j = i + 1
        while j < len(lines):
            candidate = lines[j]
            if candidate.strip() and _indent(candidate) <= class_indent:
                break
            body.append(candidate)
            j += 1

        base_indent = next((_indent(l) for l in body if l.strip()), None)
        prefix_match = _ENV_PREFIX_RE.search("\n".join(body))
        # No env_prefix is valid too — pydantic-settings then maps each field's
        # bare uppercased name directly to its env var (see services/gateway/
        # webhooks/config.py's WebhookConfig for a real example: several vars
        # sharing no common prefix, one BaseSettings class, no env_prefix set).
        prefix = prefix_match.group(1) if prefix_match else ""
        if base_indent is not None:
            for l in body:
                if not l.strip() or _indent(l) != base_indent:
                    continue
                fm = _FIELD_RE.match(l.strip())
                if fm and fm.group(1) != "model_config":
                    found.add(f"{prefix}{fm.group(1).upper()}")
        i = j
    return found


def collect_code_vars() -> set[str]:
    found: set[str] = set()
    for path in _iter_source_files():
        text = path.read_text(encoding="utf-8")
        found.update(_OS_ENV_RE.findall(text))
        found.update(_settings_vars(text))
    return found


def collect_env_example_vars() -> set[str]:
    if not ENV_EXAMPLE.exists():
        return set()
    return {
        m.group(1)
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if (m := _ENV_EXAMPLE_RE.match(line))
    }


def _selftest() -> None:
    """Regression check for the two parsers. Run with: python check_env_drift.py --selftest"""
    sample = '''
class FooConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FOO_",
        extra="ignore",
    )

    bar_baz: int = 1
    qux: str = "x"

    @property
    def derived(self) -> int:
        not_a_field: int = 99
        return self.bar_baz
'''
    assert _settings_vars(sample) == {"FOO_BAR_BAZ", "FOO_QUX"}, _settings_vars(sample)

    no_prefix_sample = '''
class BareConfig(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    some_secret: str | None = None
    other_flag: int = 60
'''
    assert _settings_vars(no_prefix_sample) == {"SOME_SECRET", "OTHER_FLAG"}, _settings_vars(no_prefix_sample)

    os_calls = 'a = os.environ.get("SOME_VAR", "x")\nb = os.getenv(\n    "OTHER_VAR",\n    "y",\n)\n'
    assert set(_OS_ENV_RE.findall(os_calls)) == {"SOME_VAR", "OTHER_VAR"}

    example = "# comment\nFOO_BAR=1\nBAZ_QUX=\n"
    assert {
        m.group(1) for line in example.splitlines() if (m := _ENV_EXAMPLE_RE.match(line))
    } == {"FOO_BAR", "BAZ_QUX"}


def collect_shell_expansion_lines() -> list[str]:
    """LGH-06: ${VAR} only expands under docker-compose, not python-dotenv/
    pydantic-settings — a bare Python process reading .env sees the literal
    string (the exact bug behind the old REDIS_URL breakage)."""
    if not ENV_EXAMPLE.exists():
        return []
    return [
        line
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if "${" in line and not line.lstrip().startswith("#")
    ]


def main() -> int:
    code_vars = collect_code_vars()
    example_vars = collect_env_example_vars()
    failed = False

    shell_expansions = collect_shell_expansion_lines()
    if shell_expansions:
        print("FAIL: .env.example uses ${VAR} shell-expansion syntax (only docker-compose expands this):")
        for line in shell_expansions:
            print(f"  {line}")
        failed = True

    undocumented_in_example = sorted(example_vars - code_vars)
    if undocumented_in_example:
        print("WARN: in .env.example but not referenced in code (may be aspirational/infra-only):")
        for var in undocumented_in_example:
            print(f"  {var}")

    undocumented_in_code = sorted(code_vars - example_vars)
    if undocumented_in_code:
        print("FAIL: referenced in code but missing from .env.example:")
        for var in undocumented_in_code:
            print(f"  {var}")
        failed = True

    if failed:
        return 1

    print(f"OK: all {len(code_vars)} code-referenced env vars are documented in .env.example, no ${{VAR}} syntax.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        print("selftest OK")
        raise SystemExit(0)
    raise SystemExit(main())
