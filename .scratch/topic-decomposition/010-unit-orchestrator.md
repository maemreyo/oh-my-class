---
title: UnitOrchestrator — stateless fan-out, topo ordering, fail isolation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the application-layer orchestrator that turns an approved sequence into child runs and drives them to completion (ADR-017 §UnitOrchestrator). It is **stateless and fully-derived**: it never holds authoritative state; on each trigger it recomputes from the DB and decides the next idempotent action.

`services/gateway/unit_orchestrator.py`:

- **Pure core**: `decide(sequence, children_states) -> list[Action]` (spawn session X, mark blocked, mark partially_complete/complete). Uses `networkx` for topological ordering over `prerequisite_sessions`.
- **Reactor**: listens on the existing event bus for child `run.completed` / `gate.pending` / `run.failed` events carrying `parent_run_id`, recomputes, and enqueues actions via `TeachingPackExecutor`.
- **Fan-out**: on unit approval, spawn the first topo layer; spawn dependents as prerequisites are satisfied. Spawn in parallel within a layer.
- **Blocking**: a session whose prerequisite failed/unapproved is `blocked` (soft) but can be force-spawned via override.
- **Fail isolation**: a failed child never fails the unit; unaffected sessions proceed.
- **Idempotent**: fan-out keyed `fanout:{unit_id}:{seq_revision}`; re-running `decide`/spawn never creates duplicate children.
- **Reconciliation sweep**: a periodic job recomputes `generating`/`in_review` units to catch missed events (at-least-once).

## Acceptance criteria

- [ ] `decide(...)` is a pure function with no I/O; orchestration I/O lives in the reactor.
- [ ] On approval, only the first topo layer spawns; dependents spawn when prerequisites are satisfied; intra-layer sessions spawn concurrently.
- [ ] A failed child leaves the unit alive; independent sessions still complete; dependents of the failure become `blocked`.
- [ ] Override force-spawns a blocked session.
- [ ] Re-invoking the orchestrator (or restarting the process) never produces duplicate child runs (idempotency key + existence check).
- [ ] The reconciliation sweep advances a unit whose triggering event was dropped.

## Detailed test suite

(Real DB + real `TeachingPackExecutor`; orchestrator core tested as a pure function. Children may use a fast deterministic graph stub at the executor seam, but DB is real.)

- [ ] `services/gateway/tests/test_unit_orchestrator_decide.py`: pure `decide` over a diamond DAG returns the correct spawn order and blocks dependents of a failed node.
- [ ] `services/gateway/tests/test_unit_orchestrator_idempotency.py`: calling fan-out twice (same `seq_revision`) creates children once; a restart mid-fan-out resumes without duplicates.
- [ ] `services/gateway/tests/test_unit_orchestrator_failure.py`: a failed session yields `partially_complete`-eligible state; independent siblings still reach approved.
- [ ] `services/gateway/tests/test_unit_orchestrator_override.py`: force-spawn moves a `blocked` session to `generating`.
- [ ] `services/gateway/tests/test_unit_orchestrator_reconcile.py`: with a suppressed event, the sweep recomputes from DB and advances the unit.
- [ ] Run `uv run pytest services/gateway/tests/test_unit_orchestrator_*.py -v`.

## Blocked by

- .scratch/topic-decomposition/002-unit-persistence-and-migration.md
- .scratch/topic-decomposition/007-graph-wiring-and-unit-gate.md
- .scratch/topic-decomposition/009-unit-context-propagation.md
