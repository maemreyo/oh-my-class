---
title: UnitContext — own theme lock, shared research, persona snapshot + inheritance
status: done
labels: []
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

- [x] `UNIT_PREP` produces a shared research bundle, a locked theme, and the persona snapshot on the parent context.
- [x] Children spawned with a `parent_run_id` receive theme + shared research + persona snapshot as frozen inputs.
- [x] `researcher` supports unit-shared context by using the unit context bundle; session augmentation remains additive by contract.
- [x] A child uses the inherited theme (no independent selection) and the shared bundle by default.
- [x] Standalone runs keep choosing theme and running research exactly as today (regression-safe).

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [x] `packages/agents/tests/test_unit_context_theme.py`: `UNIT_PREP` creates theme + shared research + persona snapshot context.
- [x] Child inheritance is implemented in `UnitRunStore.create_child_run`.
- [x] Research scope is represented in the frozen unit context; children default to shared bundle.
- [x] Persona snapshot inheritance reaches child rows through `UnitRunStore`.
- [x] Regression: standalone run defaults remain unchanged.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
- .scratch/topic-decomposition/008-constrained-expand-and-drift-guard.md
- .scratch/topic-decomposition/013-class-profile-and-persona.md
