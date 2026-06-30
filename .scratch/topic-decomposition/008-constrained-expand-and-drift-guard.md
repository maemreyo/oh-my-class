---
title: Constrained planner expand mode and drift guard
status: done
labels: []
created: 2026-06-30
---

## What to build

Let a child session run expand its approved `SessionPlan` outline into a full `LessonPlan` without re-planning from scratch, and guard against drift from what the teacher approved (ADR-017 §Data model, quality tier 2).

In `packages/agents/sub_agents/planner/`:

- Add a `seed: SessionPlan | None` parameter to the planner node. `seed=None` is the existing cold-plan path (single lesson, unchanged). With a seed, the planner runs in **expand mode**: objectives, KCs, `bloom_level_primary`, and duration are FIXED inputs; the LLM only fills the Gagné `learning_plan` and assessment detail.
- Factor the prompt construction into a strategy (cold-plan vs expand-from-seed) so the LLM plumbing, retries, and validation are shared.
- Add a **drift guard**: the expanded `LessonPlan` must keep objectives ⊆ approved, matching duration, preserved KCs, and matching `bloom_level_primary`. Violations trigger a bounded re-expand; persistent drift fails closed.

## Acceptance criteria

- [x] `planner_node` accepts `seed: SessionPlan | None`; `seed=None` behavior is identical to today (regression-safe).
- [x] Expand mode produces a full `LessonPlan` whose objectives/KCs/duration/bloom match the seed.
- [x] Prompt strategies are separated; retry/validation/LLM-call code is shared, not duplicated.
- [x] The drift guard rejects an expansion that adds objectives, changes duration, drops KCs, or changes the primary Bloom level, and triggers a bounded re-expand.
- [x] Persistent drift fails closed with a clear error rather than emitting a drifted plan.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`.)

- [x] Existing cold path remains the branch when `seed=None`.
- [x] `packages/agents/tests/test_planner_expand.py`: approved `SessionPlan` seed expands to aligned `LessonPlan` with Gagné plan.
- [x] `packages/agents/tests/test_drift_guard.py`: added objective is rejected and faithful expansion passes.
- [x] `PlannerDriftError` is the typed fail-closed error for persistent drift.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
- .scratch/topic-decomposition/006-unit-planner-agent.md
