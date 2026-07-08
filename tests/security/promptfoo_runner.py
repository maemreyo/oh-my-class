from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def run_promptfoo_security_suite(
    config_path: Path,
    *,
    output_path: Path | None = None,
    repeat: int = 1,
) -> subprocess.CompletedProcess[str]:
    """Run the suite. ``repeat`` uses promptfoo's own native repeat flag (LIC-09) —
    each test case runs ``repeat`` times; see ``majority_vote_by_scenario`` to
    aggregate into a single verdict per scenario instead of trusting one sample."""
    args = ["npx", "promptfoo", "eval", "--config", str(config_path), "--no-cache"]
    if output_path is not None:
        args.extend(["-o", str(output_path)])
    if repeat > 1:
        args.extend(["--repeat", str(repeat)])
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=300 * repeat,
    )


def majority_vote_by_scenario(report: dict[str, Any]) -> dict[str, bool]:
    """Group repeated runs by scenario description, return majority pass/fail.

    LIC-09: single-sample LLM-output assertions are not reliable (see
    test_promptfoo_real_llm.py's module docstring for the live evidence) —
    a scenario passes only if a strict majority of its repeated runs passed.
    """
    votes: dict[str, list[bool]] = {}
    for case in report["results"]["results"]:
        description = case["testCase"]["description"]
        votes.setdefault(description, []).append(bool(case["success"]))
    return {
        description: sum(results) > len(results) / 2
        for description, results in votes.items()
    }
