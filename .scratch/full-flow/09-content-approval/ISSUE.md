---
title: "Full flow 09 - Content approval and regeneration resume graph"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Make Teacher Gate 2 real. When quality-passing artifacts are ready, the teacher can approve them for export or reject them with feedback to regenerate content.

This slice is complete when the web content approval action resumes the interrupted graph and either advances to export readiness or loops back to generation.

## Acceptance criteria

- [ ] Run enters a distinct waiting-for-content-approval state after passing quality gates.
- [ ] Content approval resumes the graph and advances toward export readiness.
- [ ] Content rejection requires feedback and loops back to generation with revision count/feedback updated.
- [ ] Approval/rejection endpoints validate that the run is at the correct gate.
- [ ] Web approval modal handles content approval separately from blueprint approval.
- [ ] Duplicate or stale gate submissions return structured conflict/validation errors.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: gate discriminator identifies blueprint vs content gate from run state.
- [ ] Integration: run reaches content approval, approve advances to export readiness.
- [ ] Integration: run reaches content approval, reject with feedback loops to generation.
- [ ] Integration: reject without feedback returns 400.
- [ ] Integration: stale approval returns 409.
- [ ] Frontend test: content approval modal submits approve/reject and refreshes run detail.
- [ ] Real surface: approve content via `curl`, then verify run advances via `GET /run/{id}`.

## Blocked by

- Full flow 08 - Quality gates and healing loop
