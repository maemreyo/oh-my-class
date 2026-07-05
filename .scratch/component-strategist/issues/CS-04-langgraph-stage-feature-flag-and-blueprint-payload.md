---
title: Add provisional/final Component Strategist LangGraph passes behind feature flag
status: ready-for-agent
labels: [component-strategist, langgraph, feature-flag]
created: 2026-07-05
---

## Parent

ADR-035.

## What to build

Wire the standalone strategist into the authoritative teaching-pack graph as first-class provisional and final strategy passes around research. The feature-flagged route is `planning_blueprint -> provisional_component_strategy -> post_blueprint_research -> finalize_component_strategy -> teacher approval -> artifact_workflow`. The rollout must preserve old-run and planless compatibility.

When enabled, provisional strategy writes research questions/hypotheses for the researcher. Final strategy stores the immutable `ComponentStrategyPlan` in run state and enriches the blueprint approval payload with a compact teacher-facing strategy summary, variants, tradeoffs, fallback warnings, and feedback actions.

## Acceptance criteria

- [ ] `TeachingPackStage` includes `provisional_component_strategy` and `finalize_component_strategy`, and the graph routes `planning_blueprint -> provisional_component_strategy -> post_blueprint_research -> finalize_component_strategy -> teacher_approval` when `FEATURE_COMPONENT_STRATEGIST_V1=true`.
- [ ] Feature flag off preserves the existing route and existing tests without requiring a strategy plan.
- [ ] Stage nodes are thin adapters from `TeachingPackState` to explicit `ComponentStrategyRequest` objects and back; selector logic remains in the standalone core.
- [ ] Provisional pass stores typed research questions/hypotheses without creating the final approved strategy snapshot.
- [ ] Final pass consumes typed `ResearchSignals`, stores the immutable finalized strategy snapshot, and records any contradiction from provisional hypotheses as normal explainable behavior.
- [ ] Stage nodes record strategy start/completed/failed observability events for both passes.
- [ ] Blueprint gate payload includes recommended strategy summary, meaningful variants when present, selected learning moves, selected component types, rationale, fallback note if any, and typed feedback actions.
- [ ] Old runs without `component_strategy_plan` can still resume/render/generate through existing compatibility path.
- [ ] Integration tests cover flag-off compatibility, flag-on two-pass routing, provisional research guidance, final strategy insertion, and checkpoint/resume with an immutable stored plan.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-03 selector, scorer, and diversity core.

## References

- `docs/adr/035-component-strategist-stage.md`
- `packages/agents/teaching_pack/graph.py`
- `packages/agents/teaching_pack/stages.py`
- `packages/agents/teaching_pack/nodes.py`
- `packages/agents/teaching_pack/config.py`
- `packages/agents/events.py`
- `packages/agents/teaching_pack/teacher_memory.py`

## Implementation notes

- Do not make this a permanent parallel graph. The flag is rollout/rollback only.
- Keep teacher-facing payload compact; full score ledger belongs in observability/debug artifacts.
- Teacher approval happens once after final strategy, not after provisional strategy.
