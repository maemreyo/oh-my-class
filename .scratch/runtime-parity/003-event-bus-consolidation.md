---
title: Consolidate the two event buses onto the teaching-pack bus
status: done
labels: []
created: 2026-06-30
---

## What to build

There are two event buses: `packages/agents/events.py` (in-memory; used by the legacy router, legacy graph, and `llm/chat.py`) and `services/gateway/teaching_pack_event_bus.py` (used by the teaching-pack stream/store). This fragmentation makes run/stage SSE and cost/observability ambiguous and blocks a clean legacy decommission.

- Make `teaching_pack_event_bus` the **single** substrate for run/stage/SSE events in the authoritative runtime.
- Keep `events.py` only as the LLM/node-level event substrate **or** migrate `llm/chat.py` emission onto the unified bus — pick one and document it. Correctness (orchestration, job progress) must never depend on the in-memory bus (see topic-decomposition issue 010).
- Define a clear contract: which events flow on which bus, and how the SSE endpoints subscribe.

## Acceptance criteria

- [x] Run/stage/SSE events for the teaching-pack runtime flow through `teaching_pack_event_bus`.
- [x] `events.py` usage is reduced to a single documented role (LLM/node events) or migrated; no teaching-pack correctness path reads the in-memory bus.
- [x] SSE endpoints subscribe to the consolidated bus; the frontend live progress is unchanged.
- [x] A short doc/section records the final bus contract.

## Detailed test suite

(Real gateway app + real DB.)

- [x] `services/gateway/tests/test_unit_stream.py`: a teaching-pack/unit event is replayed through the shared SSE stream.
- [x] `services/gateway/tests/test_unit_orchestrator_events.py`: orchestration writes persisted teacher-visible unit events independent of the in-memory agent event bus.
- [x] Regression: frontend SSE consumer contract is preserved by shared event names/payloads.
- [x] Run `uv run pytest services/gateway/tests/test_unit_stream.py services/gateway/tests/test_unit_orchestrator_events.py -v`.

## Blocked by

None - can start immediately
