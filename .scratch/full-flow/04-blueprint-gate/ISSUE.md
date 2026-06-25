---
title: "Full flow 04 - Blueprint gate from real planner output"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists.** Preflight, quickstart, planner, and Gate 1 are wired into the graph. The remaining gaps are gate payload completeness, UI/event integration, and stronger real-graph test coverage.

Known current implementation:

- `packages/agents/nodes/preflight.py` rejects empty/short raw requests.
- `packages/agents/nodes/quickstart.py` sets default artifact types, theme, and research policy.
- `packages/agents/sub_agents/planner` calls LiteLLM and validates `LessonPlan`.
- `packages/agents/gates/gate_01_blueprint.py` calls `interrupt(...)` with a lesson plan payload.

## Remaining work

- [ ] Gate 1 payload must include the allowed actions and revision context required by the web approval UI, not only `gate`, `lesson_plan`, and `run_id`.
- [ ] Run status should use a stable `awaiting_blueprint_approval` or documented equivalent that web and tests agree on.
- [ ] Frontend must display the pending blueprint approval from the actual run state or real SSE gate event.
- [ ] Preflight failures should map to a structured validation-style response where appropriate, not only a generic pipeline 500.
- [ ] Tests must prove the compiled graph actually halts at Gate 1 and exposes interrupt payload, not just that state contains `lesson_plan`.

## Acceptance criteria

- [ ] Preflight rejects unsafe or structurally invalid raw requests before planner execution.
- [ ] Quickstart records run metadata needed by later slices.
- [ ] Blueprint step uses the planner agent or a test-double-friendly planner port to produce schema-valid `LessonPlan` data.
- [ ] Gate 1 payload includes lesson plan summary, approval actions, run id, and revision context.
- [ ] Run status/read model shows waiting for blueprint approval using a documented status consumed by web.
- [ ] Web can display the pending blueprint approval state from real API/SSE data.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: preflight accepts a valid teacher request and rejects empty/malformed requests.
- [ ] Unit: planner output is parsed into the canonical lesson plan contract.
- [ ] Unit: blueprint gate payload contains the fields required by the approval UI, including actions and revision context.
- [ ] Integration: create run reaches `awaiting_blueprint_approval` with lesson plan present using mocked LLM/planner.
- [ ] Integration: compiled LangGraph invocation produces an interrupt/gate payload and can be inspected before resume.
- [ ] Integration: invalid request never creates a planner call.
- [ ] Frontend test: approval UI renders the actual blueprint gate payload shape emitted by backend.
- [ ] Real surface: create a run with mock LLM enabled and inspect run detail showing blueprint approval pending.

## Blocked by

- Full flow 03 - Real progress stream
