---
title: "Full flow 09 - Content approval and regeneration resume graph"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but it inherits the approval endpoint gaps from Issue 05 and depends on the incomplete quality gate chain from Issue 08.** The same approve/reject endpoints detect `content_approval`, but tests mostly use preseeded state and mocked graph return values.

Known current implementation:

- `_require_gate()` accepts both `blueprint_approval` and `content_approval`.
- `approve()` emits `gate_approved` with the current gate type.
- `reject()` emits `gate_rejected` with feedback.
- `_derive_status()` returns `awaiting_content_approval` when `state.gate_payload.gate == "content_approval"`.

## Remaining work

- [ ] Ensure Gate 2 is reached only after canonical artifacts pass real quality gates from Issue 08.
- [ ] Use the shared run access helper from Issue 02 for content approval/rejection.
- [ ] Distinguish stale/duplicate content approval from wrong-gate validation and return structured 409 where appropriate.
- [ ] Clear/replace gate payload after content approval so stale submissions cannot replay.
- [ ] Make content rejection loop to generation through the real graph, not a mocked return state.
- [ ] Update frontend to handle content approval payload from actual SSE/run state and refresh artifacts/quality/export data after submit.

## Acceptance criteria

- [ ] Run enters a distinct waiting-for-content-approval state after passing quality gates.
- [ ] Content approval resumes the graph and advances toward export readiness.
- [ ] Content rejection requires feedback and loops back to generation with revision count/feedback updated.
- [ ] Approval/rejection endpoints validate that the run is at the correct gate and visible to the user.
- [ ] Web approval modal handles content approval separately from blueprint approval using the real payload shape.
- [ ] Duplicate or stale gate submissions return structured conflict/validation errors.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: gate discriminator identifies blueprint vs content gate from run state.
- [ ] Unit: stale content gate state maps to 409 or documented structured validation response.
- [ ] Integration: run reaches content approval through generation and quality gates, not preseeded state only.
- [ ] Integration: run reaches content approval, approve advances to export readiness through real graph resume.
- [ ] Integration: run reaches content approval, reject with feedback loops to generation through real graph resume.
- [ ] Integration: reject without feedback returns 400.
- [ ] Integration: stale approval returns 409.
- [ ] Integration: unauthorized teacher cannot approve or reject content gate.
- [ ] Frontend test: actual content approval modal submits approve/reject and refreshes run detail.
- [ ] Real surface: approve content via `curl`, then verify run advances via `GET /run/{id}`.

## Blocked by

- Full flow 08 - Quality gates and healing loop
