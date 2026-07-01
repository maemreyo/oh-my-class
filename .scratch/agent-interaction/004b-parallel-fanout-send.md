---
title: Parallel fan-out via Send (sub-agent), bounded + deterministic
status: blocked
labels: [blocked]
created: 2026-06-30
---

## What to build

Fan out **independent** work with LangGraph `Send`, where the parallelism actually lives — **inside** sub-agents. Data-dependent stages stay sequential (planner → researcher → content_creator).

- `Send` fan-out: content_creator **per-section** fill and reviewer **per-dimension** judges. Artifact-level generation moved to ADR-020 and is complete in `.scratch/artifact-send-fanout/`; unit-orchestrator child runs are separate runs, handled in `topic-decomposition`.
- This requires the sub-agent to be expressed as a **subgraph** (the "C" granularity option) — **deferred** until `agent-upgrades/003` (hierarchical outline→fill-per-section) and `agent-upgrades/004` (per-dimension judges) give the decomposition its shape. Do not build the subgraph before the decomposition exists.
- **Hard prerequisite: order-stable index-keyed reducer (`000`)** — parallel results must merge deterministically (reproducible/testable).
- **Per-run sub-fanout concurrency cap**, distinct from the worker-pool cap (composes with `scaling-resilience/001/002/003`) — bound fan-out so parallel sections don't exhaust the provider.
- **Per-section streaming** (`subgraphs=True`, namespace tags) → frontend progress ("section 3/8").

## Acceptance criteria

- [ ] Independent work fans out via `Send` (per-section, per-dimension); data-dependent steps stay sequential.
- [ ] Fan-out is bounded by a **per-run** concurrency cap (separate from the worker-pool cap); reducers are order-stable (deterministic merge under parallelism).
- [ ] Per-section progress is observable via streaming.

## Detailed test suite

- [ ] `packages/agents/tests/test_parallel_determinism.py`: parallel `Send` per-section completes in any order but merges to a deterministic result.
- [ ] `packages/agents/tests/test_subfanout_cap.py`: fan-out respects the per-run concurrency cap (does not exceed it).
- [ ] Run `uv run pytest packages/agents/tests/test_parallel_determinism.py packages/agents/tests/test_subfanout_cap.py -v`.

## Blocked by

- .scratch/agent-interaction/000-order-stable-reducer-rework.md
- .scratch/agent-interaction/003-revision-protocol.md
- agent-upgrades/003 (content_creator outline→fill-per-section subgraph)
- agent-upgrades/004 (reviewer per-dimension judges subgraph)
