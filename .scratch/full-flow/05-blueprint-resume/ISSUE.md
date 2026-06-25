---
title: "Full flow 05 - Blueprint approval and rejection resume graph"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Make Teacher Gate 1 real. Approving a blueprint should resume the exact interrupted graph thread and continue the run. Rejecting with feedback should resume or loop back with revision feedback and produce a revised blueprint.

This slice is complete when approve/reject actions from the web change the graph state, not just return a static message.

## Acceptance criteria

- [ ] `POST /run/{run_id}/approve` validates that the run is waiting at Gate 1.
- [ ] `POST /run/{run_id}/reject` requires feedback and records it on the run.
- [ ] Approval resumes the matching LangGraph interrupt and advances beyond blueprint approval.
- [ ] Rejection loops to blueprint revision with revision count/feedback updated.
- [ ] Duplicate approval/rejection of a non-waiting run returns structured conflict/validation error.
- [ ] Web approval modal calls the real endpoints and refreshes run state.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: approval command parser distinguishes approve/edit/reject and validates required feedback.
- [ ] Integration: create run to Gate 1, approve it, then `GET /run/{id}` shows advanced state.
- [ ] Integration: create run to Gate 1, reject with feedback, then state includes revision feedback/count.
- [ ] Integration: reject without feedback returns 400.
- [ ] Integration: approve unknown or non-waiting run returns 404/409.
- [ ] Frontend test: approval modal submits approve and reject flows and updates query cache.
- [ ] Real surface: create run, approve via `curl`, then verify status changed via `curl GET /run/{id}`.

## Blocked by

- Full flow 04 - Blueprint gate from real planner output
