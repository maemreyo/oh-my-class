# Issue #24: [Phase 3] Consolidate judge into AdaptiveJudge single entry

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/24
State: OPEN
Created: 2026-07-02T16:42:39Z
Updated: 2026-07-02T16:42:39Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

Judge/scoring logic is badly fragmented and the most complete implementation is not wired. `reviewer_node` imports the live `GEvalScorer`, NOT `AdaptiveJudge` — the 333-line, most complete judge, currently unwired. The fragmentation also spans `LiveReviewerQualityGate` (180 lines), `pedagogical_scorer.py`, `layer2_content/pedagogical.py`, `component_scorer.py`, and the `pedagogical_quality.py` middleware. We need one judge entry point.

This is a production-ready rebuild, NOT patching: shadow-run to prove parity, fold the good parts into `AdaptiveJudge`, cut the live path over, then **big-bang delete** the superseded scorers from the live path with a guard test (repo precedent `test_no_legacy_runtime.py`). High-readability, SoC, modular, testable.

## Scope

- [ ] Shadow-run `AdaptiveJudge` vs `GEvalScorer` on historical runs; compare scores/decisions before cutover.
- [ ] Fold `GEvalScorer`'s strengths into `AdaptiveJudge`: 3-layer weighted scoring, 3-judge majority, and the 4 bias-mitigations.
- [ ] Fold `pedagogical_scorer` into `AdaptiveJudge`'s `RubricSelector`.
- [ ] Decide keep/delete `LiveReviewerQualityGate`; if kept, document it explicitly as a deterministic pre-screen (not a competing judge).
- [ ] Cut `reviewer_node` over to `AdaptiveJudge` as the single entry.
- [ ] Delete `GEvalScorer` and `pedagogical_scorer` from the live path + add a guard test that no live path imports them.
- [ ] Add `teacher_facing_summary` to `JudgeOutput` (feeds the Phase 5 explainable gate).

## Acceptance

- [ ] Shadow-run parity report attached; no regression at cutover.
- [ ] `reviewer_node` uses `AdaptiveJudge` only; guard test fails if `GEvalScorer`/`pedagogical_scorer` re-enter the live path.
- [ ] `JudgeOutput.teacher_facing_summary` populated for every judged artifact.
- [ ] Real-LLM tests (9router :20228, model 4omc) pass, not mocks.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/03-quality-judge-consolidation.md`

## Depends on

- `[Epic][Phase 3] Core correctness` (parent) and Phase 2 state unify (`[Phase 2] Unify state model`). See milestone `agents-hardening`.

