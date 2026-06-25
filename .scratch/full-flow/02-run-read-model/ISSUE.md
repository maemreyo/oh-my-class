---
title: "Full flow 02 - Run read model"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Build the read side for runs so the dashboard can show actual run records instead of hardcoded or missing data. A teacher should be able to list their runs and inspect a specific run created by the tracer lifecycle slice.

This slice is complete when the web dashboard can load a list of real runs from the gateway and a run detail page can display real run status/current step/state summary.

## Acceptance criteria

- [ ] Authenticated `GET /run` returns only runs visible to the current teacher/admin.
- [ ] Authenticated `GET /run/{run_id}` returns the persisted run state summary for an existing run.
- [ ] Missing run id returns structured 404 with request id.
- [ ] Web runs list consumes `GET /run` successfully; no hardcoded run list is required.
- [ ] Web run detail consumes `GET /run/{run_id}` successfully and displays current status/step.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: run read model maps persisted state to the API response schema without leaking internal-only fields.
- [ ] Integration: create a run, then `GET /run` includes it.
- [ ] Integration: create a run, then `GET /run/{run_id}` returns the same id and status.
- [ ] Integration: another teacher cannot read a run they do not own unless admin.
- [ ] Integration: nonexistent run returns 404.
- [ ] Frontend test: runs page renders API-provided runs and handles empty state.
- [ ] Frontend test: run detail page renders API-provided status/current step.
- [ ] Real surface: run `curl GET /run` and `curl GET /run/{run_id}` after creating a run.

## Blocked by

- Full flow 01 - Run lifecycle tracer
