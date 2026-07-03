# Issue #24: [Phase 3] Consolidate judge into AdaptiveJudge single entry

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/24
State: OPEN
Created: 2026-07-02T16:42:39Z
Updated: 2026-07-02T16:42:39Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Progress notes

- Cut the live `reviewer_node` path over from `GEvalScorer` to `AdaptiveJudge(model="4omc")`.
- Added `teacher_facing_summary` to the canonical `JudgeOutput` Pydantic contract and regenerated/updated the generated Zod schema surface.
- Updated Layer 4 prompt/schema instructions so LLM judge responses include `teacher_facing_summary`.
- Preserved the G-Eval strengths in the live `AdaptiveJudge` path:
  - 3-layer weighted rubric via `RubricSelector`.
  - 3 independent judge calls.
  - majority vote aggregation.
  - reviewer metadata tags and diverse temperatures.
  - hard-block deterministic override remains fail-closed.
- Removed `GEvalScorer`, `PedagogicalScore`, and `score_pedagogical` from the public `packages.quality.layer4_judge` package export so callers use `AdaptiveJudge` as the single Layer 4 entry.
- Kept `LiveReviewerQualityGate` in place as the deterministic reviewer pre-screen used by `render_quality`, not as an LLM judge replacement.
- Added guard coverage in `packages/agents/tests/test_no_legacy_judge_live_path.py` so live paths under `packages/agents` and `services` fail if `GEvalScorer` or `pedagogical_scorer` re-enter.
- Added direct live-path coverage proving `reviewer_node` uses the `AdaptiveJudge` transport and returns `teacher_facing_summary` plus rubric provenance.
- Added shadow parity coverage in `packages/quality/tests/test_judge_shadow_parity.py`; the fixture compares `AdaptiveJudge` and legacy `GEvalScorer` on the same historical-style artifacts and confirms matching pass decision, score, critical issues, and teacher summary.
- Post-review cleanup tightened `teacher_facing_summary` with `max_length=500`, typed `AdaptiveJudge._call_llm_judges()` with `Rubric` instead of `Any`, and removed the confusing private `_enforce_hard_blocks` test alias in favor of importing `enforce_hard_blocks` from `hard_blocks.py`.

## Verification notes

- `uv run pytest packages/quality/tests/test_judge_shadow_parity.py packages/quality/tests/test_judge_interface.py packages/quality/tests/test_layer4_judge.py packages/agents/tests/test_no_legacy_judge_live_path.py tests/quality/test_deepeval_config.py -q` → `58 passed, 7 skipped` when real-LLM tests were not enabled.
- `OMC_RUN_REAL_LLM_TESTS=1 uv run pytest tests/quality/test_deepeval_config.py -q` → `7 passed`.
- `uv run pytest packages/quality/tests/test_judge_interface.py packages/quality/tests/test_layer4_judge.py packages/agents/tests/test_no_legacy_judge_live_path.py -q` → `57 passed`.
- Post-review rerun after cleanup: `uv run pytest packages/quality/tests/test_judge_shadow_parity.py packages/quality/tests/test_judge_interface.py packages/quality/tests/test_layer4_judge.py packages/agents/tests/test_no_legacy_judge_live_path.py tests/quality/test_deepeval_config.py -q` → `58 passed, 7 skipped`.
- Post-review real-LLM rerun: `OMC_RUN_REAL_LLM_TESTS=1 uv run pytest tests/quality/test_deepeval_config.py -q` → `7 passed`.
- Manual surface smoke: `uv run python - <<'PY' ... PY` invoked `reviewer_node` through a fake `AdaptiveJudge` transport and observed `reviewer_node_adaptive_judge_ok`.
- Guard scan: `rg "GEvalScorer|packages\.quality\.layer4_judge\.geval|pedagogical_scorer|score_pedagogical|PedagogicalScore" packages/agents services common tests -n` only reports the guard literals in `packages/agents/tests/test_no_legacy_judge_live_path.py`.
- LSP diagnostics clean for the changed Python judge/reviewer files and generated TS schema checked during the final pass.
- Five-lane post-implementation review returned PASS overall: goal verification PASS, QA PASS, code quality PASS with minor cleanup suggestions fixed, security PASS with low/medium operational finding fixed by the `teacher_facing_summary` length bound, context mining conditional PASS with remaining Phase 3 milestone items noted as out-of-scope for Issue #24.
- Round 2 remediation physically deleted `packages/quality/layer4_judge/geval.py`, `packages/quality/layer4_judge/pedagogical_scorer.py`, and legacy parity/scorer tests; the live-path guard now scans `packages/quality` in addition to `packages/agents` and `services`.
- Round 2 verification: `uv run pytest tests/test_no_parked_middleware_registered.py packages/agents/tests/test_no_legacy_judge_live_path.py packages/quality/tests/test_layer4_judge.py packages/quality/tests/test_judge_interface.py packages/agents/tests/middleware/test_middleware_suite.py -q` → 64 passed.

## Body

## Context

Judge/scoring logic is badly fragmented and the most complete implementation is not wired. `reviewer_node` imports the live `GEvalScorer`, NOT `AdaptiveJudge` — the 333-line, most complete judge, currently unwired. The fragmentation also spans `LiveReviewerQualityGate` (180 lines), `pedagogical_scorer.py`, `layer2_content/pedagogical.py`, `component_scorer.py`, and the `pedagogical_quality.py` middleware. We need one judge entry point.

This is a production-ready rebuild, NOT patching: shadow-run to prove parity, fold the good parts into `AdaptiveJudge`, cut the live path over, then **big-bang delete** the superseded scorers from the live path with a guard test (repo precedent `test_no_legacy_runtime.py`). High-readability, SoC, modular, testable.

## Scope

- [x] Shadow-run `AdaptiveJudge` vs `GEvalScorer` on historical runs; compare scores/decisions before cutover.
- [x] Fold `GEvalScorer`'s strengths into `AdaptiveJudge`: 3-layer weighted scoring, 3-judge majority, and the 4 bias-mitigations.
- [x] Fold `pedagogical_scorer` into `AdaptiveJudge`'s `RubricSelector`.
- [x] Decide keep/delete `LiveReviewerQualityGate`; if kept, document it explicitly as a deterministic pre-screen (not a competing judge).
- [x] Cut `reviewer_node` over to `AdaptiveJudge` as the single entry.
- [x] Delete `GEvalScorer` and `pedagogical_scorer` from the live path + add a guard test that no live path imports them.
- [x] Add `teacher_facing_summary` to `JudgeOutput` (feeds the Phase 5 explainable gate).

## Acceptance

- [x] Shadow-run parity report attached; no regression at cutover.
- [x] `reviewer_node` uses `AdaptiveJudge` only; guard test fails if `GEvalScorer`/`pedagogical_scorer` re-enter the live path.
- [x] `JudgeOutput.teacher_facing_summary` populated for every judged artifact.
- [x] Real-LLM tests (9router :20228, model 4omc) pass, not mocks.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/03-quality-judge-consolidation.md`

## Depends on

- `[Epic][Phase 3] Core correctness` (parent) and Phase 2 state unify (`[Phase 2] Unify state model`). See milestone `agents-hardening`.
