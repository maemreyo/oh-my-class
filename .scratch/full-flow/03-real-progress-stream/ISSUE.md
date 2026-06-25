---
title: "Full flow 03 - Real progress stream"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but backend and frontend do not agree on event semantics.** The gateway has an in-memory event store and emits named events. The web run detail page currently waits for an `interrupt` event through `onmessage`, while the backend emits `gate_waiting` and other named events.

Known current implementation:

- `services/gateway/routers/runs.py` has `_event_store`, `emit_run_event()`, `_format_sse()`, and `/run/{run_id}/status`.
- Backend emits `run_created`, `step_completed`, `gate_waiting`, `run_failed`, `gate_approved`, and `gate_rejected`.
- `apps/web/src/hooks/use-run.ts::useRunStatus()` uses `EventSource` but only exposes `onmessage`.
- `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx` opens the approval modal only for `event.type === "interrupt"`.

## Remaining work

- [ ] Choose one event protocol and document it: either emit `interrupt` events or teach the frontend to listen to named `gate_waiting`/`run_failed`/`step_completed` events.
- [ ] Make EventSource include auth if required, or document/use a token-compatible SSE strategy. Native EventSource cannot set Authorization headers.
- [ ] Ensure `/status` uses the shared run access helper from Issue 02 before opening a stream.
- [ ] Avoid treating `step_completed` and `gate_waiting` as terminal for all streams if future events can arrive after approval.
- [ ] Make timeline de-duplicate replayed stored events and live events by sequence/id.

## Acceptance criteria

- [ ] `GET /run/{run_id}/status` streams events for the requested visible run only.
- [ ] Events include at least run created, step started/updated, gate waiting, failed, and completed forms where applicable.
- [ ] Event payloads include `run_id`, event type, current step/status, and timestamp or monotonic sequence.
- [ ] Missing run id returns structured 404 before opening a stream.
- [ ] Unauthorized run id returns structured 403 before opening a stream.
- [ ] Web run detail timeline consumes the real stream and appends events without duplicate spam.
- [ ] Web run detail opens the approval UI when a gate-waiting event arrives.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: progress event serializer emits stable event/data SSE format with a sequence/id.
- [ ] Unit: progress event store appends and reads events in order.
- [ ] Unit: frontend SSE subscription registers listeners for the actual named events emitted by the backend.
- [ ] Integration: create a run and subscribe to `/status`; the stream includes the run-created/current-step event.
- [ ] Integration: subscribing to an unknown run returns 404.
- [ ] Integration: subscribing to another teacher's run returns 403.
- [ ] Frontend test: run detail page appends SSE events to the timeline.
- [ ] Frontend test: `gate_waiting` or chosen interrupt event opens the approval modal.
- [ ] Edge test: client disconnect closes the event generator without leaking subscribers.
- [ ] Real surface: use `curl -N /run/{run_id}/status` and capture at least one real event.

## Blocked by

- Full flow 01 - Run lifecycle tracer
- Full flow 02 - Run read model and ownership guard
