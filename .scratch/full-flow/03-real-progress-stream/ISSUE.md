---
title: "Full flow 03 - Real progress stream"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Replace the fake three-event SSE loop with a real progress stream derived from run state changes. A teacher watching a run should see meaningful events from the actual pipeline thread or persisted progress log.

The stream can be backed by checkpointer snapshots, an in-memory event log for development, or a DB-backed progress table, but it must reflect real run lifecycle transitions rather than a hardcoded sequence.

## Acceptance criteria

- [ ] `GET /run/{run_id}/status` streams events for the requested run only.
- [ ] Events include at least run created, step started/updated, gate waiting, failed, and completed forms where applicable.
- [ ] Event payloads include `run_id`, event type, current step/status, and timestamp or monotonic sequence.
- [ ] Missing run id returns structured 404 before opening a stream.
- [ ] Web run detail timeline consumes the real stream and appends events without duplicate spam.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: progress event serializer emits stable event/data SSE format.
- [ ] Unit: progress event store appends and reads events in order.
- [ ] Integration: create a run and subscribe to `/status`; the stream includes the run-created/current-step event.
- [ ] Integration: subscribing to an unknown run returns 404.
- [ ] Frontend test: run detail page appends SSE events to the timeline.
- [ ] Edge test: client disconnect closes the event generator without leaking tasks.
- [ ] Real surface: use `curl -N /run/{run_id}/status` and capture at least one real event.

## Blocked by

- Full flow 01 - Run lifecycle tracer
- Full flow 02 - Run read model
