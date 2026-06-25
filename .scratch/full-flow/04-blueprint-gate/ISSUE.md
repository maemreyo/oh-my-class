---
title: "Full flow 04 - Blueprint gate from real planner output"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Wire the first meaningful content step: preflight validates the teacher request, quickstart initializes run metadata, the planner produces a `LessonPlan`, and Gate 1 presents a blueprint approval payload to the teacher.

This slice is complete when a submitted request can reach a waiting-for-blueprint-approval state with a real lesson plan in run state.

## Acceptance criteria

- [ ] Preflight rejects unsafe or structurally invalid raw requests before planner execution.
- [ ] Quickstart records run metadata needed by later slices.
- [ ] Blueprint step uses the planner agent or a test-double-friendly planner port to produce schema-valid `LessonPlan` data.
- [ ] Gate 1 payload includes lesson plan summary, approval actions, run id, and revision context.
- [ ] Run status/read model shows waiting for blueprint approval.
- [ ] Web can display the pending blueprint approval state.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: preflight accepts a valid teacher request and rejects empty/malformed requests.
- [ ] Unit: planner output is parsed into the canonical lesson plan contract.
- [ ] Unit: blueprint gate payload contains the fields required by the approval UI.
- [ ] Integration: create run reaches `awaiting_blueprint_approval` with lesson plan present using mocked LLM/planner.
- [ ] Integration: invalid request never creates a planner call.
- [ ] Frontend test: approval UI can render a blueprint gate payload.
- [ ] Real surface: create a run with mock LLM enabled and inspect run detail showing blueprint approval pending.

## Blocked by

- Full flow 03 - Real progress stream
