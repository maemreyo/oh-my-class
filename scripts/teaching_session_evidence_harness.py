#!/usr/bin/env python3
"""Standalone runner for TSP-08's real TeachingSession evidence harness.

Runs the pytest-based scenario suite
(`services/gateway/tests/test_teaching_session_evidence_harness.py`) against
the real gateway/Postgres/Redis stack -- real HTTP routes, real event log,
real Redis Pub/Sub, real degraded-Redis fallback -- and writes the evidence
bundle to `.scratch/teaching-session-platform/artifacts/tsp-08-evidence.json`
as a side effect of the scenario tests themselves. Exits non-zero if any
scenario fails (this is pytest's own exit code, forwarded unchanged).

Usage:
    uv run python scripts/teaching_session_evidence_harness.py

Requires: Postgres + Redis reachable at the URLs the test module hardcodes
(same dev-stack assumption `test_teaching_session_live_router.py` makes),
schema migrated to head (`cd services/gateway && uv run alembic upgrade head`).

The two `test_harness_script_*` meta-tests in that module drive *this
script* from a subprocess to prove its exit-code contract -- they are
deselected here so a normal run doesn't recursively re-invoke itself.
"""

from __future__ import annotations

import subprocess
import sys

HARNESS_MODULE = "services/gateway/tests/test_teaching_session_evidence_harness.py"


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
