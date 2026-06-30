---
title: UnitOrchestrator — stateless, durable-substrate fan-out
status: done
labels: [done]
created: 2026-06-30
completed: 2026-07-01
---

## What to build

Add the application-layer orchestrator that turns an approved sequence into child runs and drives them to completion (ADR-017 §UnitOrchestrator). It is **stateless and fully-derived from the durable substrate** (`TeachingPackJobStore` + run rows) — never from the in-memory event bus.

`services/gateway/unit_orchestrator.py`:

- **Pure core**: `decide(sequence, children_states) -> list[Action]` returning the **full set** of ready sessions (spawn / block / mark partially_complete / complete). Uses `networkx` for topological ordering over `prerequisite_sessions`.
- **Concurrency cap**: `unit_fanout_concurrency` limits simultaneous child spawns. Phase 1 = 1 (sequential topological); Phase 2 raises it. No code fork between phases.
- **Reactor**: a hook invoked by `TeachingPackCompletionRecorder`/worker when a child settles (`completed`/`failed`/gate-pending) — it recomputes from the DB and enqueues actions via `TeachingPackExecutor`/`TeachingPackJobStore`. SSE/observability deltas flow on `teaching_pack_event_bus` (per runtime-parity issue 003); neither bus is used for correctness — the durable JobStore + run rows are.
- **Fan-out**: on unit approval, spawn the ready set (bounded by the cap); spawn dependents as prerequisites are satisfied.
- **Blocking**: a session whose prerequisite failed/unapproved is `blocked` (computed, soft) but can be force-spawned via override.
- **Fail isolation**: a failed child never fails the unit; independent sessions proceed; a failed session is retried by resuming its existing child run, not by creating a new one.
- **Idempotency**: a DB unique constraint `(parent_run_id, session_id)` plus the app-level key `fanout:{unit_id}:{seq_revision}` guarantee one child per session; re-running `decide`/spawn or restarting never creates duplicates.
- **Reconciliation sweep**: extend the existing run sweeper (`_run_teaching_pack_sweeper`) to recompute `generating`/`in_review` units from the DB (at-least-once backstop).

Gate the reactor, sweep branch, and fan-out behind `features.topic_decomposition_v1`.

## Acceptance criteria

- [x] `decide(...)` is pure (no I/O) and returns the full ready set; orchestration I/O lives in the reactor.
- [x] `unit_fanout_concurrency` caps concurrent spawns; with cap=1 sessions run one-at-a-time in topo order.
- [x] The reactor is triggered by the durable completion-recorder hook, not the in-memory event bus; correctness holds if every in-memory event is lost.
- [x] A failed child leaves the unit alive; dependents become `blocked`; independent siblings still complete; retry resumes the existing child run.
- [x] Override force-spawns a blocked session.
- [x] The DB unique constraint `(parent_run_id, session_id)` is enforced; re-invoking fan-out or restarting mid-fan-out never creates duplicate children.
- [x] The reconciliation sweep advances a unit whose triggering hook was missed.

## Detailed test suite

(Real DB + real `TeachingPackExecutor`/`JobStore`; `decide` tested as a pure function.)

- [x] `services/gateway/tests/test_unit_orchestrator_decide.py`: pure `decide` over a diamond DAG returns the correct ready set and blocks dependents of a failed node.
- [x] `services/gateway/tests/test_unit_orchestrator_concurrency.py`: cap=1 spawns sequentially; cap=N spawns the whole ready layer.
- [x] `services/gateway/tests/test_unit_orchestrator_idempotency.py`: the `(parent_run_id, session_id)` unique constraint rejects a duplicate child; a restart mid-fan-out resumes without duplicates.
- [x] `services/gateway/tests/test_unit_orchestrator_failure.py`: a failed session keeps the unit alive; siblings reach approved; retry resumes the existing child (no new row).
- [x] `services/gateway/tests/test_unit_orchestrator_reconcile.py`: with the hook suppressed, the sweep recomputes from the DB and advances the unit (proves no reliance on in-memory events).
- [x] Run `uv run pytest services/gateway/tests/test_unit_orchestrator_*.py -v`.

## Blocked by

- .scratch/topic-decomposition/002-unit-persistence-and-migration.md
- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
- .scratch/topic-decomposition/009-unit-context-propagation.md
