---
title: "Promptfoo red-team: N-sample majority vote per scenario; unskip test_deepeval_real_llm.py"
status: ready-for-agent
labels: [testing, llm-integration, security]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 9
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 7.

## What to build

`tests/security/test_promptfoo_real_llm.py` proves the K-12 safety red-team suite genuinely invokes 9Router (no mocks) but deliberately does not gate pass/fail per scenario — its own docstring states every one of the 5 scenarios failed at least once across 9 live runs, on a different scenario each time, even at `temperature=0`, and that "making red-team results a real pass/fail gate would need N-sample majority voting per case."

`packages/quality/layer4_judge/majority_vote.py`'s `majority_vote()` already implements this pattern for `AdaptiveJudge` (3-judge vote, ≥2/3 pass + average-score threshold — wired at `packages/quality/layer4_judge/judge_interface.py:229-230`). Reuse this pattern (or the function directly, if `JudgeOutput`'s shape can represent a red-team scenario's outcome) instead of writing new voting logic for promptfoo.

Separately: `tests/quality/test_deepeval_real_llm.py` is `pytest.mark.skip`'d with the reason "Blocked on fixing AdaptiveJudge's ungoverned litellm transport" — that transport was fixed in commit `ec10283` (`packages/quality/layer4_judge/judge_transport.py` now routes through `LLMClient`). The skip reason is stale.

## Acceptance criteria

- [ ] Each promptfoo scenario runs N ≥ 3 times (odd number for a clean majority); a scenario passes only if a majority of runs pass. Per-run results are still printed in full for human review, as today.
- [ ] Voting logic reuses `packages.quality.layer4_judge.majority_vote`'s approach/utilities rather than duplicating vote-counting logic.
- [ ] `tests/quality/test_deepeval_real_llm.py`'s `pytestmark = pytest.mark.skip(...)` is removed; the test is run with `OMC_RUN_REAL_LLM_TESTS=1 pytest -m real_llm tests/quality/test_deepeval_real_llm.py` to confirm it passes against `4omc` before committing. If it still fails for a different reason, update the skip reason to the new, accurate blocker instead of leaving the stale one.
- [ ] `real-llm-release-gate.yml` continues to work unchanged (it already runs `-m real_llm` broadly).

## Blocked by

Nothing.
