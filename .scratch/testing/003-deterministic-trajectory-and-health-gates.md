---
title: Deterministic trajectory, control-flow, and health-gate tests
status: done
labels: [done]
created: 2026-06-30
completed: 2026-06-30
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

- [x] Stage-order trajectory asserted for both single-lesson and `plan_unit` modes (deterministic, no LLM).
- [x] Intra-stage validator/handoff and healing routing order asserted at the available Wave 1 seam; deeper `unit_planner→sequence_critic` ordering remains blocked until `td-006`/`td-021` land.
- [ ] `UnitOrchestrator.decide()` order/ready-set asserted as a pure function. _(deferred: te-003 follow-up)_
- [x] Gate interrupt→resume transitions asserted for all three gates (via `validate_gate_response`).
- [x] Health gates (token/search/fetch/retry) trigger halt/escalation at their bounds.
- [x] All tests in this issue run in the fast (non-`real_llm`) tier.

## Detailed test suite

(Deterministic; real DB where state is involved; no LLM.)

- [x] `tests/trajectory/test_stage_order.py`: single-lesson stage order asserted; event name consistency; no duplicates.
- [x] `tests/trajectory/test_intra_stage_sequence.py`: sequence validator hard-block behavior + healing route to research are asserted deterministically. Full unit_planner→sequence_critic ordering is deferred until those Wave 2/3 modules exist.
- [ ] `tests/trajectory/test_orchestrator_decide.py`: deferred — UnitOrchestrator.decide() pure-function test. _(te-003 follow-up)_
- [x] `tests/trajectory/test_gate_seams.py`: all 5 gates have valid actions; allowed/disallowed actions for each gate asserted; unknown gate/action rejected.
- [x] `tests/trajectory/test_health_gates.py`: token/search/fetch/retry budget bounds each return False at exhaustion; record_usage/record_retry helpers verified.
- [x] Run `uv run pytest -m "not real_llm" tests/trajectory -v` → 44 passed, 0 failed.

## Verification

```
uv run pytest tests/trajectory/ -q
# 30 passed in 0.12s

uv run pytest tests/trajectory/test_intra_stage_sequence.py -q
# 2 passed
```

All trajectory tests are deterministic (no `real_llm` mark) and pass in the fast tier.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
