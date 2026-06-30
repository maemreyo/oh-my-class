---
title: Coordination, parallelism (Send), and interaction observability
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Define coordination semantics and make the multi-agent interaction observable — using LangGraph **`Send`** for parallelism and the existing trace/event substrate.

- **Parallelism boundaries**: sequential where data-dependent (planner → researcher → content_creator); **`Send` fan-out** where independent — content_creator per-artifact + per-section fill, reviewer per-dimension judges, unit orchestrator child runs. No forced parallelism across data dependencies.
- **Concurrency control**: bound fan-out (SubagentLimit / concurrency cap); **order-stable reducers** so parallel results merge deterministically (reproducible/testable).
- **Observability of the interaction graph**: every handoff, `Command(goto)` revision, `Send` fan-out, and BaseStore read/write emits a trace span / RunEvent → an observable "who-called-who / revised-what / read-what" graph (feeds testing trajectory + reviewer calibration).

## Acceptance criteria

- [ ] Independent work fans out via `Send` (per-section, per-dimension, child runs); data-dependent steps stay sequential.
- [ ] Fan-out is bounded by a concurrency cap; reducers are order-stable (deterministic merge under parallelism).
- [ ] Handoffs, revisions, Send fan-outs, and Store accesses are traced to Langfuse/RunEvents.
- [ ] The interaction graph is reconstructable from traces for debugging/calibration.

## Detailed test suite

- [ ] `packages/agents/tests/test_parallel_determinism.py`: parallel `Send` per-section completes in any order but merges to a deterministic result.
- [ ] `packages/agents/tests/test_interaction_trace.py`: a run emits trace spans for each handoff/revision/Send/Store-access; the interaction graph is reconstructable.
- [ ] Run `uv run pytest packages/agents/tests/test_parallel_determinism.py packages/agents/tests/test_interaction_trace.py -v`.

## Blocked by

- .scratch/agent-interaction/003-command-revision-protocol.md
