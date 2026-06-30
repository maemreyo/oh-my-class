---
title: UnitContext — own theme lock, shared research, persona snapshot + inheritance
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Own the full production and inheritance of `UnitContext` so a unit is visually and factually consistent and cost-efficient (ADR-017 §UnitContext). Issue 007 created `UNIT_PREP` as a placeholder; this slice fills its logic and wires child inheritance.

In the teaching-pack stage runtime:

- **`UNIT_PREP` stage produces UnitContext**: lock the theme (proposed during `UNIT_PLANNING`, approved at the unit gate), compute the shared research bundle once (reuse `researcher_node` at unit scope), and attach the persona snapshot (issue 013). Persist all three on the parent run row (`shared_research`, theme, `persona_snapshot`).
- **Children inherit frozen**: when the orchestrator spawns a child (issue 010), it injects theme + shared research + persona snapshot as frozen contract/state inputs.
- **`researcher` enhancement**: add a `scope` — unit-shared (one pass) vs session-augment (thin, additive, only when a sub-topic diverges). Children default to using the shared bundle (no second full research).
- **`content_creator` / visual**: a child honors the inherited theme instead of choosing its own; child research defaults to the shared bundle.

Standalone runs (no `parent_run_id`) are unaffected — they choose theme and research exactly as today.

## Acceptance criteria

- [ ] `UNIT_PREP` persists a shared research bundle, a locked theme, and the persona snapshot on the parent row.
- [ ] Children spawned with a `parent_run_id` receive theme + shared research + persona snapshot as frozen inputs.
- [ ] `researcher` supports unit-shared vs session-augment scope; augmentation is additive, not a full re-research.
- [ ] A child uses the inherited theme (no independent selection) and the shared bundle by default.
- [ ] Standalone runs keep choosing theme and running research exactly as today (regression-safe).

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [ ] `packages/agents/tests/test_unit_prep_context.py`: `UNIT_PREP` persists theme + shared research + persona snapshot on the parent.
- [ ] `packages/agents/tests/test_unit_context_theme.py`: two children of one unit render with the same locked theme; a standalone run still selects its own.
- [ ] `packages/agents/tests/test_researcher_scope.py`: unit-shared scope runs one research pass; children reuse it (no second call) unless a divergence flag triggers a bounded augment.
- [ ] `packages/agents/tests/test_unit_context_persona.py`: the persona snapshot reaches the child planner state and influences the plan.
- [ ] Regression: a standalone run's theme/research behavior is unchanged.
- [ ] Run `uv run pytest packages/agents/tests/test_unit_prep_context.py packages/agents/tests/test_unit_context_*.py packages/agents/tests/test_researcher_scope.py -v`.

## Blocked by

- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
- .scratch/topic-decomposition/008-constrained-expand-and-drift-guard.md
- .scratch/topic-decomposition/013-class-profile-and-persona.md
