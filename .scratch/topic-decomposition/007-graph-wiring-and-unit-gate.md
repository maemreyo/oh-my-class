---
title: Graph wiring — plan_unit branch, UNIT_APPROVAL gate, unit-prep
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Wire the parent unit path into the existing LangGraph pipeline (ADR-017 §Flow parent) so a `plan_unit` run plans a sequence, gates it once, prepares shared unit context, and ends — leaving fan-out to the orchestrator (issue 010). The single-lesson path must stay byte-for-byte unchanged.

In `packages/agents/graph.py`:

- Add `step_02b_triage`, `unit_planner` (issue 006), `gate_unit_approval`, and `step_unit_prep` nodes.
- Branch by mode at the blueprint stage: `mode="plan_unit"` → `unit_planner → gate_unit_approval → step_unit_prep → END`; otherwise the existing `planner_node` path.
- `gate_unit_approval` uses `interrupt()` (reuse the gate mechanism) with a new gate name `UNIT_APPROVAL`; actions approve/reject/edit; `edit` carries reorder/add/remove/edit-session payloads; approval freezes the sequence.
- `step_unit_prep` locks the theme and computes the shared research bundle once (issue 009), persists them on the parent row, then routes to END.

Register `UNIT_APPROVAL` in `services/gateway/teaching_pack_gate_registry.py` with allowed actions approve/reject/edit.

## Acceptance criteria

- [ ] A `plan_unit` run traverses `… → step_02b_triage → unit_planner → gate_unit_approval → step_unit_prep → END`.
- [ ] `route_after_blueprint`-style routing selects the unit path only when `mode="plan_unit"`; all other modes are unchanged.
- [ ] `UNIT_APPROVAL` is a registered gate with allowed actions approve/reject/edit; `validate_gate_response` accepts them and rejects others.
- [ ] `edit` at the gate mutates the in-flight sequence (reorder/add/remove/edit) and re-runs the validator before re-presenting; `approve` freezes the sequence.
- [ ] `reject` routes back to `unit_planner` with feedback.
- [ ] `step_unit_prep` persists locked theme + shared research on the parent row and the parent run ends (does not wait for children).
- [ ] Existing single-lesson integration tests pass unchanged.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`; reuse the LangGraph integration harness.)

- [ ] `services/gateway/tests/test_unit_gate_integration.py`: a `plan_unit` run reaches `gate_unit_approval`, interrupts with a `UNIT_APPROVAL` payload containing the sequence + `grounding_status`.
- [ ] same file: resuming with `approve` freezes the sequence and runs `step_unit_prep`, persisting theme + shared research; the run reaches END.
- [ ] same file: resuming with `edit` (reorder two sessions) preserves `session_id` references and re-validates before re-presenting.
- [ ] same file: resuming with `reject` re-enters `unit_planner`.
- [ ] `services/gateway/tests/test_unit_gate_registry.py`: `UNIT_APPROVAL` allows approve/reject/edit and rejects `answer`.
- [ ] Regression: `uv run pytest packages/agents/tests/test_generate_flow_integration.py services/gateway/tests/test_blueprint_gate_integration.py -v` still passes.
- [ ] Run `uv run pytest services/gateway/tests/test_unit_gate_integration.py -v`.

## Blocked by

- .scratch/topic-decomposition/002-unit-persistence-and-migration.md
- .scratch/topic-decomposition/006-unit-planner-agent.md
