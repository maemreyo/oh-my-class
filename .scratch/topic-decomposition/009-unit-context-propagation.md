---
title: UnitContext propagation — theme, shared research, persona to children
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make children inherit frozen unit-level context so a unit is visually and factually consistent and cost-efficient (ADR-017 §UnitContext). The parent computes once; children inherit.

- **Theme**: proposed during `unit_planner`, approved at the unit gate, locked on the parent row. Child `step_06_visual_engine` runs in an "inherit" mode that consumes the locked theme instead of choosing its own.
- **Shared research**: computed once in `step_unit_prep` (reuse `researcher_node` at unit scope), persisted on the parent. Child `step_07_research` defaults to **skip** (uses shared bundle) and runs a thin **augment** pass only when its sub-topic diverges.
- **Persona snapshot**: the frozen `ClassProfile` snapshot (issue 013) is injected into every child's planning state.

This slice wires inheritance into the child generate path; it must not change standalone-run behavior when no `parent_run_id` is present.

## Acceptance criteria

- [ ] `step_unit_prep` produces and persists a shared research bundle and a locked theme on the parent row.
- [ ] Child runs spawned with a `parent_run_id` receive theme, shared research, and persona snapshot as frozen inputs.
- [ ] `step_06_visual_engine` honors an inherited theme (no independent theme selection) when a unit theme is present.
- [ ] `step_07_research` uses the shared bundle by default and only augments when a divergence flag is set; augmentation is additive, not a full re-research.
- [ ] Standalone runs (no `parent_run_id`) keep choosing theme and running research exactly as today.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [ ] `packages/agents/tests/test_unit_context_theme.py`: two child runs of one unit render with the same locked theme; a standalone run still selects its own theme.
- [ ] `packages/agents/tests/test_unit_context_research.py`: child runs reuse the shared bundle (no second research call) unless a divergence flag triggers a bounded augment pass.
- [ ] `packages/agents/tests/test_unit_context_persona.py`: the persona snapshot reaches the child planner state and influences the generated plan (e.g. duration/methodology reflect the persona).
- [ ] Regression: a standalone run's research/theme behavior is unchanged.
- [ ] Run `uv run pytest packages/agents/tests/test_unit_context_*.py -v`.

## Blocked by

- .scratch/topic-decomposition/007-graph-wiring-and-unit-gate.md
- .scratch/topic-decomposition/008-constrained-expand-and-drift-guard.md
- .scratch/topic-decomposition/013-class-profile-and-persona.md
