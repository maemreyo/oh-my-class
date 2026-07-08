"""CI guard: block raw LLM-gateway (port 20228) references outside the sanctioned probes.

`packages/llm_client/` is exempt wholesale: it *is* the sanctioned client,
so its own config default and docstrings referencing the gateway port are
definitional, not a bypass.

Beyond that, only these files are allowed to hardcode the gateway port —
they're health/release probes that must hit the gateway directly, or wire
one of those probes, rather than going through LLMClient's chat-completion
abstraction:
    - packages/agents/llm/smoke.py
    - services/gateway/provider_evidence.py
    - services/gateway/routers/release_evidence.py (wires provider_evidence's
      default target; does not call httpx itself)

Every other call site should go through LLMClient (packages/llm_client),
which encapsulates cost/rate/audit governance. import-linter (see
docs/adr, LGH-01) can ban `httpx` imports outright, but can't tell "httpx
used to probe the gateway" from "httpx used to bypass LLMClient" — this
literal-grep check catches the latter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SCAN_DIRS: Final[tuple[str, ...]] = ("packages", "services")
GATEWAY_PORT: Final[str] = "20228"
EXEMPT_DIRS: Final[tuple[str, ...]] = ("packages/llm_client/",)
ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "packages/agents/llm/smoke.py",
        "services/gateway/provider_evidence.py",
        "services/gateway/routers/release_evidence.py",
    },
)


def find_violations() -> list[str]:
    violations: list[str] = []
    for scan_dir in SCAN_DIRS:
        for path in (ROOT / scan_dir).rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if (
                "/tests/" in f"/{relative}"
                or relative in ALLOWLIST
                or relative.startswith(EXEMPT_DIRS)
            ):
                continue
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if GATEWAY_PORT in line:
                    violations.append(f"{relative}:{line_number}: {line.strip()}")
    return violations


def main() -> int:
    violations = find_violations()
    if violations:
        sys.stderr.write(
            "Raw gateway port literal ('20228') found outside the allowlisted "
            f"probes ({', '.join(sorted(ALLOWLIST))}):\n",
        )
        sys.stderr.write("\n".join(violations) + "\n")
        sys.stderr.write(
            "\nRoute LLM calls through LLMClient (packages/llm_client) instead of "
            "hitting the gateway directly. If this is a new sanctioned probe, add "
            "it to ALLOWLIST in scripts/check_no_raw_gateway_calls.py.\n",
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
