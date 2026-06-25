---
title: "Full flow 02 - Run read model and ownership guard"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation, security]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but the ownership boundary is incomplete.** `GET /run` filters by current teacher/admin, and `_to_run_response()` maps some state fields into a read model. Direct run-scoped endpoints still do not enforce teacher ownership.

Known current implementation:

- `services/gateway/routers/runs.py::list_runs()` filters runs by `teacher_id` for teachers and allows admins.
- `services/gateway/routers/runs.py::get_run()` returns any run found by id without checking owner/admin.
- `_to_run_response()` enriches state with a `quality` summary, but still exposes the full state blob.

## Remaining work

- [ ] Add a shared run access helper that returns the run only when the authenticated user owns it or is admin.
- [ ] Apply the access helper to `GET /run/{run_id}`, SSE status, artifacts, exports, approve, and reject endpoints.
- [ ] Decide which fields are safe in `RunResponse.state`; do not leak internal-only fields or teacher-only artifact answers through the run detail blob.
- [ ] Make `POST /run` reuse `_to_run_response()` or an equivalent mapper for response consistency.
- [ ] Add typed status/current step fields that the web dashboard can consume without scanning arbitrary state.

## Acceptance criteria

- [ ] Authenticated `GET /run` returns only runs visible to the current teacher/admin.
- [ ] Authenticated `GET /run/{run_id}` returns the persisted run state summary for an existing visible run.
- [ ] Another teacher cannot read, stream, approve, reject, fetch artifacts, or fetch exports for a run they do not own unless admin.
- [ ] Missing run id returns structured 404 with request id.
- [ ] Forbidden run access returns structured 403 with request id.
- [ ] Web runs list consumes `GET /run` successfully; no hardcoded run list is required.
- [ ] Web run detail consumes `GET /run/{run_id}` successfully and displays current status/step.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: run read model maps persisted state to the API response schema without leaking internal-only fields.
- [ ] Unit: run access helper permits owner/admin and denies other teachers.
- [ ] Integration: create a run, then `GET /run` includes it for the owner.
- [ ] Integration: create a run, then `GET /run/{run_id}` returns the same id and status for the owner.
- [ ] Integration: another teacher cannot read a run they do not own unless admin.
- [ ] Integration: another teacher cannot call `/status`, `/artifacts`, `/exports`, `/approve`, or `/reject` for the run.
- [ ] Integration: nonexistent run returns 404.
- [ ] Frontend test: runs page renders API-provided runs and handles empty state.
- [ ] Frontend test: run detail page renders API-provided status/current step.
- [ ] Real surface: run `curl GET /run` and `curl GET /run/{run_id}` after creating a run.

## Blocked by

- Full flow 01 - Run lifecycle tracer
