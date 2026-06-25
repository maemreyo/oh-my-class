---
title: "Full flow 05 - Blueprint approval and rejection resume graph"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but action validation, edit flow, ownership, and stale-gate handling are incomplete.** Approve/reject endpoints call `Command(resume=...)` and update in-memory run state. Tests mostly mock `graph.ainvoke` to return prebuilt states, so they do not prove real interrupt/resume behavior.

Known current implementation:

- `services/gateway/routers/approvals.py::approve()` resumes with `{"action": "approve"}`.
- `services/gateway/routers/approvals.py::reject()` requires feedback and resumes with `{"action": "reject"}`.
- `_require_gate()` checks `state.gate_payload.gate` is one of `blueprint_approval` or `content_approval`.

## Remaining work

- [ ] Use the shared run access helper from Issue 02 so only the owner/admin can approve or reject.
- [ ] Change `ApprovalRequest.action` from arbitrary `str` to a strict enum and validate that `/approve` only accepts approve/edit and `/reject` only accepts reject.
- [ ] Implement or explicitly defer the edit path. If supported, pass edited lesson plan through `Command(resume=...)` using the gate contract.
- [ ] Return 409 Conflict or a documented structured validation error for stale/duplicate gate submissions.
- [ ] Clear or replace stale `gate_payload` after successful resume so the same gate cannot be resubmitted.
- [ ] Add real compiled-graph interrupt/resume tests instead of only mocked return-state tests.

## Acceptance criteria

- [ ] `POST /run/{run_id}/approve` validates that the run is waiting at Gate 1 and belongs to the requester or requester is admin.
- [ ] `POST /run/{run_id}/reject` requires feedback and records it on the run.
- [ ] Approval resumes the matching LangGraph interrupt and advances beyond blueprint approval.
- [ ] Rejection loops to blueprint revision with revision count/feedback updated.
- [ ] Duplicate approval/rejection of a non-waiting run returns structured conflict/validation error.
- [ ] Edit action is either implemented end-to-end or rejected with a typed unsupported-action error.
- [ ] Web approval modal calls the real endpoints and refreshes run state.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: approval command parser distinguishes approve/edit/reject and validates required feedback.
- [ ] Unit: stale/non-gate state maps to 409 or documented structured validation response.
- [ ] Integration: create run to Gate 1, approve it through the real compiled graph, then `GET /run/{id}` shows advanced state.
- [ ] Integration: create run to Gate 1, reject with feedback through the real compiled graph, then state includes revision feedback/count.
- [ ] Integration: reject without feedback returns 400.
- [ ] Integration: approve unknown, unauthorized, or non-waiting run returns 404/403/409 as appropriate.
- [ ] Frontend test: actual approval modal component submits approve and reject flows and updates query cache.
- [ ] Real surface: create run, approve via `curl`, then verify status changed via `curl GET /run/{id}`.

## Blocked by

- Full flow 04 - Blueprint gate from real planner output
