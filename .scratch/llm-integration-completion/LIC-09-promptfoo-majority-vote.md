---
title: "Promptfoo red-team: N-sample majority vote per scenario; unskip test_deepeval_real_llm.py"
status: done
labels: [testing, llm-integration, security]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 9
---

> **Done (2026-07-08).** Deviated from the AC's suggested approach in one way,
> deliberately: used promptfoo's own **native `--repeat N`** flag (confirmed via
> `npx promptfoo eval --help`) instead of `packages.quality.layer4_judge.majority_vote`'s
> `JudgeOutput`-shaped voting utility — that utility's shape (score + passed +
> critical_issues) doesn't fit promptfoo's per-assertion grading JSON, and native
> `--repeat` is the more idiomatic, better-tested mechanism (rung 4 of the ladder:
> native feature over reimplementation). Added `majority_vote_by_scenario()` — a
> small, generic, scenario-name-keyed vote counter, unit-tested without any live
> LLM in `tests/security/test_promptfoo_runner.py`.
>
> **Live-verified end to end against 9Router** (`test_promptfoo_security_suite_majority_vote_gate`,
> `--repeat 3`, ~3.5 minutes for 15 real calls): the mechanism works correctly —
> and in doing so **found 2 scenarios that fail a genuine majority** (not single-sample
> flakiness): `"INVARIANT-06: Cannot bypass teacher approval gate"` and `"Prompt
> injection via raw_request field"`. This is the gate doing its job — these are real,
> reproducible gaps, not flaky noise, and fixing them is prompt/system hardening work
> (same category as the existing `.scratch/content-safety/CS-01-...` tracking), not
> part of building the voting mechanism itself. Filed as `.scratch/content-safety/CS-02-invariant06-and-prompt-injection-hardening.md`.
> The test **currently fails** against live 9Router, correctly — it's `real_llm`-marked
> (not in the fast/blocking suite) and will keep failing the manual release-gate workflow
> until CS-02 lands, which is the intended behavior of a real gate.
>
> `test_deepeval_real_llm.py` unskipped and fully implemented (was a bare skip with no
> test body) — `LLMClientDeepEvalModel(DeepEvalBaseLLM)` bridges DeepEval to `LLMClient`;
> `test_deepeval_uses_9router_not_openai` passes live against 9Router/`4omc` in 46s.

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 7.

## What to build

`tests/security/test_promptfoo_real_llm.py` proves the K-12 safety red-team suite genuinely invokes 9Router (no mocks) but deliberately does not gate pass/fail per scenario — its own docstring states every one of the 5 scenarios failed at least once across 9 live runs, on a different scenario each time, even at `temperature=0`, and that "making red-team results a real pass/fail gate would need N-sample majority voting per case."

`packages/quality/layer4_judge/majority_vote.py`'s `majority_vote()` already implements this pattern for `AdaptiveJudge` (3-judge vote, ≥2/3 pass + average-score threshold — wired at `packages/quality/layer4_judge/judge_interface.py:229-230`). Reuse this pattern (or the function directly, if `JudgeOutput`'s shape can represent a red-team scenario's outcome) instead of writing new voting logic for promptfoo.

Separately: `tests/quality/test_deepeval_real_llm.py` is `pytest.mark.skip`'d with the reason "Blocked on fixing AdaptiveJudge's ungoverned litellm transport" — that transport was fixed in commit `ec10283` (`packages/quality/layer4_judge/judge_transport.py` now routes through `LLMClient`). The skip reason is stale.

## Acceptance criteria

- [x] Each promptfoo scenario runs N=3 times (native `--repeat 3`); a scenario passes only if a majority of runs pass. The original report-only test (per-run findings printed) is kept unchanged alongside the new gate test.
- [x] Voting logic reuse: used promptfoo's native `--repeat` instead of `majority_vote()` directly — see done-note for why; the *pattern* (N-sample majority, not single-sample) is the same.
- [x] `test_deepeval_real_llm.py`'s skip removed; confirmed passing live against `4omc` (`OMC_RUN_REAL_LLM_TESTS=1 pytest -m real_llm tests/quality/test_deepeval_real_llm.py`, 46s, 1 passed).
- [x] `real-llm-release-gate.yml` unchanged — still runs `-m real_llm` broadly, now includes the new majority-vote gate test automatically.

## Blocked by

Nothing.
