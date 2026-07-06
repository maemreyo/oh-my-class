---
title: Add blueprint objective normalization and strategy lineage
status: completed
labels: [component-strategist, planner, contracts, testing]
created: 2026-07-05
---

## Parent

ADR-039.

## What to build

Upgrade the blueprint/objective contract and normalization path so Component Strategist can target stable learning objectives instead of fragile list positions or raw text. New production planner output should include objective importance, assessability, and assessment intent where possible. The system normalizer owns objective IDs/revisions and strategy snapshots reference the exact blueprint/objective revision they were derived from.

This issue is the seam between Planner output, teacher blueprint edits, Component Strategist request construction, and strategy revision invalidation.

## Acceptance criteria

- [x] Planner/blueprint contracts support objective `importance: core | supporting | extension`, `assessable`, and `assessment_intent: none | formative | summative | exam_prep | diagnostic`.
- [x] System normalization assigns deterministic objective IDs and objective revisions; IDs are stable across reorder/light edits and change or rev when learning target semantics change.
- [x] If objective importance/assessability is missing, compatibility inference is deterministic and records inference reason.
- [x] Strategy snapshots store `blueprint_revision_id` and objective refs with `objective_id` + `objective_revision`.
- [x] Semantic blueprint/objective changes invalidate the finalized strategy and trigger recomputation; cosmetic changes preserve strategy with recorded reason.
- [x] Conservative system detection distinguishes semantic-vs-cosmetic changes, with explicit edit-intent override when the app/teacher marks an edit as wording-only or learning-target change.
- [x] Blueprint approval supports teacher-visible objective priority and assessability edits as typed strategy revision feedback, not free-form prompt patches.
- [x] Uncovered core objectives block final strategy with typed options; supporting/extension deferrals are recorded, and extension deferrals produce visible non-blocking notes.
- [x] Objective coverage matrix records pack-level coverage across artifact projections and avoids requiring every artifact to cover every objective.
- [x] Tests cover objective ID stability on reorder, light edit preservation, semantic edit invalidation, inference fallback, teacher priority edit revision, core objective block, and extension deferral note.

## Completion notes

- Added objective-lineage normalization contracts for deterministic IDs/revisions, inference metadata, and semantic-vs-cosmetic revision decisions.
- Extended planner/blueprint objective fields for importance, assessability, and assessment intent.
- Wired the component-strategy stage to normalize planner objectives before building selector requests.
- Added objective coverage snapshots, core-objective blocking, and extension deferral notes in selector output.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-04 LangGraph stage and blueprint payload.

## References

- `docs/adr/039-component-strategy-blueprint-and-delivery-semantics.md`
- `docs/adr/035-component-strategist-stage.md`
- `common/contracts/lesson_plan.py`
- `common/contracts/run_contract.py`
- `packages/agents/sub_agents/planner/staged_engine.py`
- `packages/agents/sub_agents/planner/nodes.py`
- `packages/agents/teaching_pack/nodes.py`
- `.scratch/component-strategist/issues/CS-01-contracts-and-immutable-strategy-snapshot.md`

## Implementation notes

- Objective identity is system-owned. Do not trust LLM-generated IDs without normalization.
- Do not add a separate pre-strategy teacher gate solely for objectives; use the blueprint/strategy approval panel revision flow.
- Strategy emits typed replan recommendations when objectives are impossible; it does not call Planner directly.
