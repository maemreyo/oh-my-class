---
title: "Full flow 01 - Run lifecycle tracer"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but this issue is not complete.** `POST /run` now creates a run id, builds an initial state, invokes `app.state.graph.ainvoke(...)`, stores the result in `app.state.runs`, and returns a `RunResponse`. The strict review found contract and durability gaps that must be fixed before this slice is accepted.

Known current implementation:

- `services/gateway/routers/runs.py::build_initial_state()` creates the base state.
- `services/gateway/routers/runs.py::create_run()` invokes the compiled graph and stores state in memory.
- `services/gateway/main.py` builds a graph in lifespan and initializes `app.state.runs`.

## Remaining work

- [ ] Return the same read-model shape from `POST /run` that `GET /run/{run_id}` returns, including top-level `current_step`, `artifact_types`, and topic/progress metadata when available.
- [ ] Include explicit LangGraph thread/config metadata in the initial state or persisted run metadata so the thread can be inspected and resumed intentionally.
- [ ] Validate that `teacher_id` in the request cannot spoof the authenticated user. Either derive it from auth or reject mismatches.
- [ ] On graph invocation failure, persist a failed run record or explicitly document why failed creations are not persisted; do not leave only an event with no run record.
- [ ] Keep the graph invocation real, but bounded and deterministic in tests via injected mocked LLMs, not by replacing the whole graph with a state-returning mock.

## Acceptance criteria

- [ ] Authenticated `POST /run` accepts a lesson request and returns a schema-matching response containing `run_id`, `status`, and current state/progress metadata.
- [ ] The run is persisted in the gateway run store and survives a follow-up request within the same dev process.
- [ ] The initial state includes teacher id, raw request, class info, run id, defaults for artifact/export fields, and a LangGraph thread/config id.
- [ ] The gateway invokes the compiled graph or a deliberately bounded first graph step; it must not be a pure stub.
- [ ] Failures during run creation return structured error responses with `X-Request-ID` and do not lose run failure context.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: state factory builds a complete `OhMyClassState` from a minimal run request and includes thread/config metadata.
- [ ] Unit: invalid/missing request fields are rejected by FastAPI/Pydantic with structured validation error.
- [ ] Unit: request `teacher_id` mismatch with authenticated user is rejected or normalized.
- [ ] Integration: authenticated `POST /run` creates a persisted run and returns HTTP 200 with the expected response schema, not only `{run_id,status,state}`.
- [ ] Integration: unauthenticated `POST /run` returns 401/403 and does not create a run.
- [ ] Integration: graph invocation failure records a failed run or returns a structured 500 without losing request id/run id context.
- [ ] Real graph integration: use a compiled graph with mocked LLM responses through Gate 1; do not replace `graph.ainvoke` with a canned state.
- [ ] Real surface: `curl` login or test token flow, then `curl POST /run`; capture response body and request id.
- [ ] Regression: existing gateway error-handler and request-id tests stay green.

## Blocked by

None - can start immediately
