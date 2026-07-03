# Issue #27: [Phase 3] Scoped replan — heal per artifact_id, not whole batch

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/27
State: OPEN
Created: 2026-07-02T16:42:57Z
Updated: 2026-07-02T16:42:57Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Progress notes

- Rewrote `packages/agents/healing/strategies/replan.py` to use `TeachingPackState` field names only.
- Scoped replan now reads `fail_context["artifact_id"]` and clears only the failed artifact plus downstream dependents:
  - `lesson` clears `worksheet`, `quiz`, `drill`, and `recap`.
  - `quiz` clears `recap`.
  - other artifact failures clear only the failed artifact.
- Full replan remains reserved for upstream `planning_blueprint` and `post_blueprint_research` failures, or for missing artifact scope.
- Scoped clearing applies consistently to `artifact_chunks`, `artifacts`, `artifact_workflow_states`, `rendered_snapshots`, and `quality_scores.reports`.
- Added `packages/agents/healing/tests/test_replan_strategy.py` with regression coverage for a wave-2 `quiz` failure preserving wave-1 `lesson` and unrelated artifacts while clearing `quiz` and dependent `recap`.

## Verification evidence

- Red check before implementation: `uv run pytest packages/agents/healing/tests/test_orchestrator.py::TestReplanStrategy -q` failed because `artifact_chunks` was `None` and upstream failures still routed to `artifact_workflow`.
- `uv run pytest packages/agents/healing/tests/test_orchestrator.py packages/agents/healing/tests/test_replan_strategy.py packages/agents/tests/teaching_pack/test_healing_recovery.py packages/agents/tests/teaching_pack/test_render_quality.py -q` → `51 passed`.
- LSP diagnostics clean for:
  - `packages/agents/healing/strategies/replan.py`
  - `packages/agents/healing/tests/test_orchestrator.py`
  - `packages/agents/healing/tests/test_replan_strategy.py`
- Legacy-field guard: `rg -n "review_results|judge_score|schema_valid|content_review_passed" packages/agents/healing/strategies/replan.py` → no output.
- Manual surface smoke through `replan.apply()` with failed `quiz-1` preserved `lesson-1`, removed `quiz-1` and `recap-1`, and kept `quality_recovery_route == "artifact_workflow"`: `issue-027 scoped replan smoke: PASS`.
- Pure LOC audit after splitting tests:
  - `packages/agents/healing/strategies/replan.py` → `95`
  - `packages/agents/healing/tests/test_orchestrator.py` → `208`
  - `packages/agents/healing/tests/test_replan_strategy.py` → `75`

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
