---
title: Stage wiring — plan_unit branch, UNIT_APPROVAL gate, UNIT_PREP skeleton
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Wire the parent unit path into the **teaching-pack stage runtime** (ADR-017 §Topology) so a `plan_unit` run plans a sequence, gates it once, runs a unit-prep stage, and ends — leaving fan-out to the orchestrator (issue 010). The single-lesson stage sequence stays unchanged.

This slice owns the **graph/gate/parent-path skeleton only**. The contents of `UNIT_PREP` (theme lock + shared research + persona snapshot) are owned by issue 009 — here `UNIT_PREP` is a registered placeholder stage.

In `packages/agents/teaching_pack/`:

- Add stages `UNIT_PLANNING` and `UNIT_PREP` to `TeachingPackStage`; add `unit_planner` (issue 006) as the `UNIT_PLANNING` stage node.
- Mode-aware routing in `build_teaching_pack_graph`: `mode="plan_unit"` → `TRIAGE → UNIT_PLANNING → (unit_approval interrupt) → UNIT_PREP → END`; `mode="generate_pack"` → the existing stage sequence (children take this path).
- Register `UNIT_APPROVAL` (`unit_approval`) in `services/gateway/teaching_pack_gate_registry.py` with allowed actions approve/reject/edit; the gate is a stage-boundary interrupt opened/resumed via `POST /teaching-packs/runs/{id}/resume` (same pattern as `blueprint_approval`/`content_approval`).
- `edit` mutates the in-flight sequence (reorder/add/remove/edit), bumps `seq_revision`, and **re-runs `SequenceConsistencyValidator`** before re-presenting; `remove`-with-dependents and `edit`-causing-cycle are rejected with a structured reason; `approve` freezes the sequence; `reject` re-enters `UNIT_PLANNING`.

## Acceptance criteria

- [ ] A `plan_unit` run traverses `SETUP_CONTRACT → TRIAGE → UNIT_PLANNING → unit_approval → UNIT_PREP → END` and never runs `artifact_workflow`/`render_quality`/`teacher_approval`/`export_finalize`.
- [ ] Mode routing selects the unit branch only when `contract.mode="plan_unit"`; all other modes are unchanged.
- [ ] `UNIT_APPROVAL` is registered with approve/reject/edit; `validate_gate_response` accepts them and rejects others; it is driven via the teaching-pack resume endpoint.
- [ ] `edit` re-validates and bumps `seq_revision`; removing a session with dependents and edits that create a cycle are rejected with a structured message; `approve` freezes the sequence.
- [ ] `UNIT_PREP` exists as a placeholder stage that routes to END (its production logic is issue 009).
- [ ] Existing single-lesson stage runs and their integration tests pass unchanged.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`; teaching-pack executor + checkpointer.)

- [ ] `services/gateway/tests/test_unit_stage_flow.py`: a `plan_unit` run reaches the `unit_approval` interrupt with a payload carrying the sequence + `grounding_status`.
- [ ] same file: resume `approve` freezes the sequence, runs `UNIT_PREP`, reaches END; resume `reject` re-enters `UNIT_PLANNING`.
- [ ] `services/gateway/tests/test_unit_gate_edit.py`: `edit` reorder preserves `session_id` references and bumps `seq_revision`; remove-with-dependents and edit-causes-cycle are rejected.
- [ ] `services/gateway/tests/test_unit_gate_registry.py`: `unit_approval` allows approve/reject/edit and rejects `answer`.
- [ ] Regression: existing teaching-pack flow/gate integration tests pass unchanged.
- [ ] Run `uv run pytest services/gateway/tests/test_unit_stage_flow.py services/gateway/tests/test_unit_gate_edit.py services/gateway/tests/test_unit_gate_registry.py -v`.

## Blocked by

- .scratch/topic-decomposition/002-unit-persistence-and-migration.md
- .scratch/topic-decomposition/006-unit-planner-agent.md
