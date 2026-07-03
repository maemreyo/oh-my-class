# Issue #15: [Epic][Phase 2] State unification + observability backbone

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/15
State: OPEN
Created: 2026-07-02T16:42:06Z
Updated: 2026-07-02T16:42:06Z
Labels: enhancement, agents-refactor, phase-2
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Completion notes

- Child Issue #22 is DONE: state unification and `StageEnum` guard coverage are in place.
- Child Issue #23 is DONE: `ObservabilityEvent` flows through the package event bus, gateway worker persistence, `run_events`, and SSE replay.
- Verification evidence is recorded on the child tickets, including focused Python suites and worker/router regressions.

## Body

## Context

Two independent state models coexist and the healing/middleware layers still write legacy field names. This is the single biggest source of correctness drift in the system. On top of it we have no real observability backbone — there is no shared event stream feeding either ops or the teacher UI. This epic unifies the state model and stands up the observability backbone. It is the **foundation** that Phase 3 correctness work depends on.

Concrete evidence this is foundational: `healing/strategies/replan.py` writes **legacy** `OhMyClassState` field names (`artifacts`, `review_results`, `judge_score`, `schema_valid`) rather than `TeachingPackState` names (`artifact_chunks`, `quality_scores`). Until state is unified, healing cannot reliably reason about what failed.

This is a production-ready rebuild, NOT patching. Deletions follow big-bang physical deletion plus guard tests (see `test_no_legacy_runtime.py`); the result must be high-readability, SoC, modular, testable.

## Scope

Children of this epic (separate issues in this milestone):

- [ ] Unify state model — delete `OhMyClassState`, introduce `StageEnum`.
- [ ] Observability backbone — `ObservabilityEvent`, `run_events` table, `INVARIANT_REGISTRY`.

Coordination:

- [ ] The observability backbone is the **single** source for both the ops dashboard and the Phase 5 teacher live-status. Do not build two pipelines.
- [ ] State unify must land before Phase 3 so `fail_context` and stage identity are reliable.

## Acceptance

- [x] Both child issues closed with their guard/meta tests passing.
- [x] No live code path reads or writes `OhMyClassState`.
- [x] Events flow into `run_events` and are consumable by a single downstream reader.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/02-state-model-unification.md`, `docs/reports/agents/06-testing-and-observability-strategy.md`

## Depends on

- Phase 1 dead-code removal (`[Epic][Phase 1] Dead-code removal & documentation drift`) so the tree is clean before restructuring state. See milestone `agents-hardening`.
