# Issue #22: [Phase 2] Unify state model — delete OhMyClassState, introduce StageEnum

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/22
State: OPEN
Created: 2026-07-02T16:42:34Z
Updated: 2026-07-02T16:42:34Z
Labels: enhancement, agents-refactor, phase-2
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

Two state models coexist: the legacy `OhMyClassState` (`state.py`) and `TeachingPackState`. This split is the root cause of correctness drift. Hard evidence: `healing/strategies/replan.py` writes **legacy** `OhMyClassState` field names — `artifacts`, `review_results`, `judge_score`, `schema_valid` — instead of the `TeachingPackState` names `artifact_chunks`, `quality_scores`. Healing therefore mutates fields the live runtime does not read. Additionally, stage counting drifts across the codebase (8 vs 9 vs 13 stages) because there is no single enum of record.

ADR-018 notes teaching-pack currently has scoped-regeneration only and that legacy healing is not fully wired — unifying state is the prerequisite to fixing that.

This is a production-ready rebuild, NOT patching: after a parity proof, migrate everything to `TeachingPackState`, then **big-bang delete** `state.py` with a guard test (repo precedent `test_no_legacy_runtime.py`). High-readability, SoC, modular, testable.

## Scope

- [ ] **Parity test first:** run `OhMyClassState` vs `TeachingPackState` over historical runs and prove equivalent/derivable data before any deletion.
- [ ] Migrate `healing/*` (including `strategies/replan.py`) and all middleware to read/write `TeachingPackState` field names (`artifact_chunks`, `quality_scores`, ...). Remove the legacy field writes.
- [ ] Delete `state.py` (`OhMyClassState`) big-bang and add a guard test (`test_no_legacy_state.py` style, patterned on `test_no_legacy_runtime.py`).
- [ ] Introduce a single `StageEnum` as the source of truth; replace the 8/9/13 stage-count drift with it. `current_step` becomes a `StageEnum`.

## Acceptance

- [ ] Parity test passes on historical runs.
- [ ] Guard test fails if `OhMyClassState` / legacy field names reappear.
- [ ] Every stage reference resolves through `StageEnum`; `current_step` is typed as `StageEnum`.
- [ ] `replan.py` writes only `TeachingPackState` field names.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/02-state-model-unification.md`

## Depends on

- `[Epic][Phase 2] State unification + observability backbone` (parent). Foundational — blocks all of Phase 3, especially scoped replan (needs reliable `fail_context`). See milestone `agents-hardening`.

