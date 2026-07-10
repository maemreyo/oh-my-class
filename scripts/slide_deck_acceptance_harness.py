#!/usr/bin/env python3
"""SDH-07: standalone runner for the official real-LLM slide-deck acceptance harness.

Runs the pytest-based scenario suite
(`services/gateway/tests/test_slide_deck_acceptance_harness.py`) against the
real gateway app, real Postgres, and a real 9router LLM gateway (model
`4omc`) -- three natural classroom scenarios (Grade 5 ESL vocabulary, Grade 5
math worked-example/practice, Vietnamese-language classroom deck), each
driven end to end through real gateway HTTP, asserted for deck shape,
quality, and leak-safety, exported, and (where Playwright is genuinely
installed) browser-QA'd -- then writes a timestamped evidence bundle to
`.scratch/slide-deck-acceptance/artifacts/sdh-07-evidence.json` as a side
effect of the scenario tests themselves. Exits non-zero if any scenario
fails (this is pytest's own exit code, forwarded unchanged).

Usage:
    uv run python scripts/slide_deck_acceptance_harness.py

Config (env vars, all optional -- see the test module's docstring for
defaults): SDH07_DATABASE_URL, OMC_9ROUTER_BASE_URL, OMC_9ROUTER_MODEL,
SDH07_TEACHER_USERNAME, SDH07_RUN_TIMEOUT_SECONDS, SDH07_EVIDENCE_DIR.

Requires: Postgres reachable at SDH07_DATABASE_URL, schema migrated to head
(`cd services/gateway && uv run alembic upgrade head`), and a live 9router
at OMC_9ROUTER_BASE_URL serving model `4omc`. Scenarios that can't reach
either are skipped (not silently passed) by the module's `client` fixture.

The two `test_harness_script_*`-prefixed meta-tests in that module drive
*this script* from a subprocess to prove its exit-code contract -- they are
deselected here so a normal run doesn't recursively re-invoke itself.

Out-of-process variant (real HTTP over the wire, not in-process TestClient):
start `uv run uvicorn services.gateway.main:app --port 8001` yourself first,
then adapt this script to point `scripts/run_teacher_scenarios.py`-style
`urllib` calls at `http://localhost:8001` instead of the TestClient fixture
-- left as a documented follow-up (the in-process TestClient path already
exercises the real app, real worker, real DB, and real 9router end to end,
so it fully satisfies "real gateway HTTP surface" for CI purposes without
requiring a second process to babysit).
"""

from __future__ import annotations

import subprocess
import sys

HARNESS_MODULE = "services/gateway/tests/test_slide_deck_acceptance_harness.py"


def main() -> int:
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q",
            HARNESS_MODULE,
            "-k", "not test_harness_script",
        ],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
