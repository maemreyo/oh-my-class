---
title: Deterministic trajectory, control-flow, and health-gate tests
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Assert the system's **control flow** deterministically (per-commit, no LLM), since the authoritative runtime is stage-based — there is no Lead-Agent delegation to trace.

- **Stage trajectory**: the teaching-pack graph traverses the expected stage order (`setup_contract → … → export_finalize`), and the mode-aware `plan_unit` branch traverses `TRIAGE → UNIT_PLANNING → unit_approval → UNIT_PREP → END`. Assert via `completed_stages` / stage events.
- **Intra-stage sequence**: `unit_planner → sequence_critic → validator` (topic-decomposition); healing recovery routing (runtime-parity 002).
- **Orchestrator**: `UnitOrchestrator.decide()` ready-set + topological order + fan-out spawn order (pure-function).
- **Gate seams**: `interrupt → resume` transitions for `contract_confirmation` / `unit_approval` / `content_approval`.
- **Health gates**: enforce timeout (120s), token budget, step/stage limit, revision limit (3) — assert the run halts/escalates at each bound.

No Lead-Agent-delegation trajectory (not in the runtime). If a Lead Agent is later wired, add then.

## Acceptance criteria

- [ ] Stage-order trajectory asserted for both single-lesson and `plan_unit` modes (deterministic, no LLM).
- [ ] Intra-stage `unit_planner→sequence_critic→validator` and healing routing order asserted.
- [ ] `UnitOrchestrator.decide()` order/ready-set asserted as a pure function.
- [ ] Gate interrupt→resume transitions asserted for all three gates.
- [ ] Health gates (timeout/token/step/revision) trigger halt/escalation at their bounds.
- [ ] All tests in this issue run in the fast (non-`real_llm`) tier.

## Detailed test suite

(Deterministic; real DB where state is involved; no LLM.)

- [ ] `tests/trajectory/test_stage_order.py`: single-lesson and `plan_unit` runs record the expected `completed_stages` sequence.
- [ ] `tests/trajectory/test_intra_stage_sequence.py`: `unit_planner→sequence_critic→validator` ordering holds; healing routing escalates after `max_healing_attempts`.
- [ ] `tests/trajectory/test_orchestrator_decide.py`: `decide()` over a known DAG returns the correct ordered ready-set.
- [ ] `tests/trajectory/test_gate_seams.py`: each gate interrupts and resumes via `/teaching-packs/runs/{id}/resume`.
- [ ] `tests/trajectory/test_health_gates.py`: timeout/token/step/revision bounds each halt or escalate.
- [ ] Run `uv run pytest -m "not real_llm" tests/trajectory -v`.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
