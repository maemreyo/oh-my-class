"""Real invocation of the Promptfoo K-12 safety red-team suite.

Marked real_llm — run with: OMC_RUN_REAL_LLM_TESTS=1 pytest -m real_llm tests/security/

This actually shells out to `npx promptfoo eval` against a live 9Router
(promptfoo.yaml's provider is promptfoo_provider.py, which calls the same
governed LLMClient every other real LLM call in this repo uses — 9Router
returns Content-Type: text/event-stream with an SSE trailer even for
non-streaming requests, which promptfoo's own built-in HTTP provider cannot
parse, so this suite cannot use promptfoo's built-in openai-compatible
provider; see promptfoo_provider.py's docstring).

The prior version of this test (removed 2026-07-08, see
tests/security/test_security_stubs.py) mocked subprocess.run entirely and
only asserted the command-line args were constructed correctly — it never
ran Promptfoo for real, matching the 2026-07-01 audit's exact finding
("promptfoo.yaml never invoked... comment only, no CI step").

Scope of `test_promptfoo_security_suite_runs_against_live_9router`, after 9 live
runs of evidence (2026-07-08): it proves the suite genuinely executes against
9Router (zero provider/runner errors, zero mocks) — it does NOT gate on
individual red-team pass/fail. Every one of the 5 scenarios in promptfoo.yaml
has been observed to fail at least once across those runs, on a DIFFERENT
scenario each time — single-sample LLM-output assertions are not a reliable
hard gate at this model's current sampling behavior, even at temperature=0.

`test_promptfoo_security_suite_majority_vote_gate` (LIC-09, added 2026-07-08)
is the real hard gate: uses promptfoo's own native `--repeat` flag (not a
custom Python retry loop) to run every scenario N times, then requires a
strict majority to pass per scenario via `majority_vote_by_scenario`. This
replaces the "report only" approach for CI/release-gate purposes; the
report-only test above stays as a cheap "did it even run" smoke check.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.security.promptfoo_runner import majority_vote_by_scenario, run_promptfoo_security_suite

CONFIG_PATH = Path("tests/security/promptfoo.yaml")


@pytest.mark.real_llm
def test_promptfoo_security_suite_runs_against_live_9router(tmp_path) -> None:
    """Runs the real red-team suite against live 9Router and asserts only
    that it genuinely executed (zero provider/runner errors) — see module
    docstring for why individual red-team results are reported, not gated.
    """
    output_path = tmp_path / "promptfoo_result.json"
    result = run_promptfoo_security_suite(CONFIG_PATH, output_path=output_path)

    report = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
    stats = report["results"]["stats"] if report else None

    assert stats is not None, (
        f"promptfoo produced no readable output — a runner/config problem:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert stats["errors"] == 0, (
        f"promptfoo reported provider/runner errors — the suite did not "
        f"actually exercise 9Router for every test case. stats={stats}"
    )

    findings = [
        f"{case['testCase']['description']}: "
        + "; ".join(
            f"[{c['assertion']['type']}] {c.get('reason', '')}"
            for c in case.get("gradingResult", {}).get("componentResults", [])
            if not c["pass"]
        )
        for case in report["results"]["results"]
        if not case["success"]
    ]
    if findings:
        print(
            f"\npromptfoo red-team findings this run ({stats['failures']}/"
            f"{stats['successes'] + stats['failures']}) — for human review, "
            f"not a test failure (see module docstring):\n" + "\n".join(findings)
        )


@pytest.mark.real_llm
def test_promptfoo_security_suite_majority_vote_gate(tmp_path) -> None:
    """LIC-09: the real hard gate — each scenario must win a strict majority
    across N repeats (promptfoo's native --repeat), not a single sample."""
    output_path = tmp_path / "promptfoo_result.json"
    result = run_promptfoo_security_suite(CONFIG_PATH, output_path=output_path, repeat=3)

    report = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
    assert report is not None, (
        f"promptfoo produced no readable output:\nstdout={result.stdout}\nstderr={result.stderr}"
    )

    verdicts = majority_vote_by_scenario(report)
    failed_scenarios = [description for description, passed in verdicts.items() if not passed]

    assert not failed_scenarios, (
        f"these scenarios failed a majority vote across 3 repeats: {failed_scenarios}\n"
        f"(a single bad sample no longer fails this gate — a majority must fail)"
    )