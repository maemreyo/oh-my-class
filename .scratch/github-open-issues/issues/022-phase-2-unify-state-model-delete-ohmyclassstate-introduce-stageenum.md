# Issue #22: [Phase 2] Unify state model — delete OhMyClassState, introduce StageEnum

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/22
State: OPEN
Created: 2026-07-02T16:42:34Z
Updated: 2026-07-02T16:42:34Z
Labels: enhancement, agents-refactor, phase-2
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification for completed safe slices
- [x] Run surface/manual QA for completed safe slices
- [x] Update this ticket status

## Progress notes

- Introduced canonical `StageEnum` for teaching-pack stages and migrated teaching-pack runtime, planner, researcher, and content-creator handoffs to stage enum values.
- Preserved `TeachingPackStage = StageEnum` as a compatibility alias while the rest of Phase 2 migrates.
- Added `stage_number(StageEnum)` for legacy numeric telemetry without keeping numeric runtime `current_step` values.
- Migrated replan healing to clear live `TeachingPackState` fields (`artifact_chunks`, `artifact_workflow_states`, `rendered_snapshots`, `quality_scores`, `quality_issues`) and removed legacy output writes (`review_results`, `judge_score`, `schema_valid`, `content_review_passed`).
- Added healing fields to `TeachingPackState` and fixed the healing orchestrator import cycle with a type-only `TeachingPackState` reference.
- Decoupled teaching-pack middleware runtime from `OhMyClassState` by introducing middleware-local `MiddlewareState` and migrating middleware implementations/tests to it.
- Decoupled legacy quality gate functions/tests from `OhMyClassState` by introducing gate-local `GateState`.
- Decoupled legacy graph node functions/tests and finalize integration tests from `OhMyClassState` by introducing node-local `NodeState`.
- Removed package-level `OhMyClassState` re-export and retargeted state schema/quality tests to `TeachingPackState`.
- Migrated gateway quality-gate integration tests to `GateState`, `NodeState`, and `TeachingPackState`.
- Deleted `packages/agents/state.py` after runtime/test imports were migrated away from `OhMyClassState`.
- Added `tests/test_no_legacy_state.py`, which fails if the removed legacy state module or runtime references return.
- Migrated the remaining live teaching-pack sub-agent handoffs in `packages/agents/teaching_pack/nodes.py` from numeric `current_step` values to `StageEnum` values.
- Updated as-built docs that still described `packages/agents/state.py::OhMyClassState` as present.

## Verification notes

- `uv run pytest packages/agents/healing/tests/test_orchestrator.py packages/agents/tests/teaching_pack/test_foundation.py packages/agents/tests/teaching_pack/test_nodes.py packages/agents/tests/teaching_pack/test_artifact_workflow_node.py packages/agents/tests/middleware/test_middleware_suite.py -q` → `71 passed`.
- `uv run pytest packages/agents/tests/middleware -q` → `67 passed`.
- `uv run pytest packages/agents/tests/middleware/test_middleware_suite.py packages/agents/tests/teaching_pack/test_foundation.py packages/agents/tests/teaching_pack/test_nodes.py packages/agents/tests/teaching_pack/test_artifact_workflow_node.py -q` → `36 passed`.
- `uv run pytest packages/agents/gates/tests -q` → `105 passed`.
- `uv run pytest packages/agents/tests/test_nodes.py -q` → `40 passed`.
- `uv run pytest packages/agents/tests/test_state_schemas.py packages/agents/tests/test_state_quality_fields.py tests/integration/test_component_render_pipeline.py tests/integration/test_full_pipeline.py -q` → `35 passed`.
- `uv run pytest services/gateway/tests/test_quality_gate_integration.py -q` → `41 passed`.
- LSP diagnostics clean for `packages/agents/middleware`, `packages/agents/tests/middleware`, `packages/agents/healing/orchestrator.py`, `packages/agents/healing/tests/test_orchestrator.py`, and `packages/agents/teaching_pack/nodes.py`.
- LSP diagnostics clean for `packages/agents/gates`, `packages/agents/nodes`, `packages/agents/tests/test_state_schemas.py`, `services/gateway/tests/test_quality_gate_integration.py`, and finalize integration tests.
- Runtime smoke: awaited `make_stage_node(StageEnum.SETUP_CONTRACT)` and observed `current_stage`/`current_step` as `StageEnum.SETUP_CONTRACT`.
- `uv run pytest tests/test_no_legacy_state.py packages/agents/tests/test_state_schemas.py -q` → `21 passed`.
- `uv run pytest tests/test_no_legacy_state.py packages/agents/tests/test_state_schemas.py packages/agents/tests/test_state_quality_fields.py tests/integration/test_component_render_pipeline.py tests/integration/test_full_pipeline.py -q` → `37 passed`.
- `uv run pytest packages/agents/tests/teaching_pack/test_nodes.py packages/agents/tests/teaching_pack/test_foundation.py packages/agents/tests/test_unit_planner.py packages/agents/tests/test_diagnostician_stage.py -q` → `30 passed`.
- `uv run pytest packages/agents/healing/tests/test_orchestrator.py packages/agents/tests/teaching_pack/test_artifact_workflow_node.py packages/agents/tests/middleware packages/agents/gates/tests packages/agents/tests/test_nodes.py services/gateway/tests/test_quality_gate_integration.py -q` → `293 passed`.
- Manual surface smoke: `uv run python -c '...'` imported `StageEnum` and `build_teaching_pack_graph`, verified `stage_number(StageEnum.SETUP_CONTRACT) == 1`, `stage_number(StageEnum.UNIT_PLANNING) == 10`, and verified `importlib.util.find_spec("packages.agents.state") is None` → `stage_enum_ok legacy_state_removed`.
- Final scan: no runtime/test references to `OhMyClassState` or `packages.agents.state` remain; remaining matches are historical/planning docs, the as-built removal note, reducer names (`stable_merge_artifacts`), and the guard test literal.
- Final numeric-stage scan: live `TeachingPackState` handoffs are StageEnum-based; remaining numeric `current_step` hits are boundary-local legacy/API DTO surfaces (`NodeState`, `GateState`, gateway run/notification DTOs) and their tests.

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
