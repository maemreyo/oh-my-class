---
title: Interaction observability — trace handoffs, reroutes, Store access
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make the multi-agent interaction **observable**, using the existing Langfuse + `RunEvent` substrate (`ops-observability/001`, already wired). Independent of parallelism (`Send` is `004b`).

- Every **seam handoff** (`001`), **revision reroute** (`003`), and **BaseStore read/write** (`002a`) emits a trace span / `RunEvent`.
- From the traces, reconstruct a **"who-called-who / revised-what / read-what" interaction graph** for debugging and calibration.
- Feeds the testing trajectory layers (`testing/002`, `testing/003`) and reviewer calibration (`agent-upgrades/004`).
- Degrades gracefully when Langfuse is unconfigured (matches existing `observability/tracing.py` no-op behavior).

## Acceptance criteria

- [ ] Handoffs, revisions, and Store accesses are traced to Langfuse / `RunEvent`.
- [ ] The interaction graph is reconstructable from traces for debugging/calibration.
- [ ] Tracing degrades to no-op when Langfuse is unconfigured (no hard dependency).

## Detailed test suite

- [ ] `packages/agents/tests/test_interaction_trace.py`: a run emits trace spans for each handoff / revision / Store-access; the interaction graph is reconstructable.
- [ ] Run `uv run pytest packages/agents/tests/test_interaction_trace.py -v`.

## Blocked by

- .scratch/agent-interaction/001-seam-contract-layer.md
- .scratch/agent-interaction/002a-store-substrate.md
