---
title: Constrained planner expand mode and drift guard
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Let a child session run expand its approved `SessionPlan` outline into a full `LessonPlan` without re-planning from scratch, and guard against drift from what the teacher approved (ADR-017 §Data model, quality tier 2).

In `packages/agents/sub_agents/planner/`:

- Add a `seed: SessionPlan | None` parameter to the planner node. `seed=None` is the existing cold-plan path (single lesson, unchanged). With a seed, the planner runs in **expand mode**: objectives, KCs, `bloom_level_primary`, and duration are FIXED inputs; the LLM only fills the Gagné `learning_plan` and assessment detail.
- Factor the prompt construction into a strategy (cold-plan vs expand-from-seed) so the LLM plumbing, retries, and validation are shared.
- Add a **drift guard**: the expanded `LessonPlan` must keep objectives ⊆ approved, matching duration, preserved KCs, and matching `bloom_level_primary`. Violations trigger a bounded re-expand; persistent drift fails closed.

## Acceptance criteria

- [ ] `planner_node` accepts `seed: SessionPlan | None`; `seed=None` behavior is identical to today (regression-safe).
- [ ] Expand mode produces a full `LessonPlan` whose objectives/KCs/duration/bloom match the seed.
- [ ] Prompt strategies are separated; retry/validation/LLM-call code is shared, not duplicated.
- [ ] The drift guard rejects an expansion that adds objectives, changes duration, drops KCs, or changes the primary Bloom level, and triggers a bounded re-expand.
- [ ] Persistent drift fails closed with a clear error rather than emitting a drifted plan.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`.)

- [ ] `packages/agents/tests/test_planner_seed_regression.py`: `planner_node` with `seed=None` produces the same shape/behavior as the current planner (existing planner tests still pass).
- [ ] `packages/agents/tests/test_planner_expand.py`: given an approved `SessionPlan` seed, the expanded `LessonPlan` carries the seed's objectives/KCs/duration/bloom and adds a Gagné `learning_plan`.
- [ ] `packages/agents/tests/test_drift_guard.py`: an expansion that adds an objective or changes duration is rejected by the drift guard; a faithful expansion passes.
- [ ] `packages/agents/tests/test_drift_guard.py`: persistent drift across bounded retries raises a typed error (fail-closed).
- [ ] Run `uv run pytest packages/agents/tests/test_planner_*.py packages/agents/tests/test_drift_guard.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
- .scratch/topic-decomposition/006-unit-planner-agent.md
