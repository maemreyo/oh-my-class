# Issue #27: [Phase 3] Scoped replan — heal per artifact_id, not whole batch

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/27
State: OPEN
Created: 2026-07-02T16:42:57Z
Updated: 2026-07-02T16:42:57Z
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

Replan currently wipes the **entire** batch on a single failure. Evidence: `healing/strategies/replan.py` clears everything and does so using **legacy `OhMyClassState` field names** (`artifacts`, `review_results`, `judge_score`, `schema_valid`). This is both wasteful (re-generates artifacts that were fine) and incorrect (mutates fields the live runtime does not read). ADR-018 notes teaching-pack has scoped-regeneration only and legacy healing is not fully wired — this issue makes healing scoped and correct.

This is a production-ready rebuild, NOT patching. It depends on the Phase 2 state unify so `fail_context["artifact_id"]` is reliable. High-readability, SoC, modular, testable.

## Scope

- [ ] `HealingOrchestrator.heal()` reads `fail_context["artifact_id"]` to identify the single failed artifact.
- [ ] Replan clears **only** the failed artifact plus its downstream dependents per the Send fan-out graph: worksheet/quiz/drill depend on lesson; recap depends on lesson + quiz.
- [ ] Full replan is reserved **only** for `planning_blueprint` / `post_blueprint_research` failures (upstream of fan-out).
- [ ] Rewrite `replan.py` to use `TeachingPackState` field names (`artifact_chunks`, `quality_scores`) — no legacy field writes.
- [ ] Test: fail exactly 1 artifact in wave 2 and assert wave-1 artifacts are NOT wiped; assert only the failed artifact + its dependents are cleared.

## Acceptance

- [ ] Scoped-replan test passes: wave-1 artifacts survive a wave-2 single-artifact failure.
- [ ] Full replan triggers only for blueprint/research failures.
- [ ] `replan.py` contains zero legacy `OhMyClassState` field names.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`, `docs/adr/017-topic-decomposition-and-unit-fan-out.md`
- Verdict: `docs/reports/agents/05-scalability-and-resilience.md`, `docs/reports/agents/02-state-model-unification.md`

## Depends on

- Phase 2 state unify (`[Phase 2] Unify state model`) so `fail_context` and field names are reliable. Parent: `[Epic][Phase 3] Core correctness`. Scoped actions align with the Phase 5 teacher gate. See milestone `agents-hardening`.

