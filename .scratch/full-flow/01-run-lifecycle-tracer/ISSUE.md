---
title: "Full flow 01 - Run lifecycle tracer"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Implement the first real tracer bullet for the product: a teacher can submit a lesson request through the gateway, the system creates a durable run, initializes a valid pipeline state, starts a real LangGraph thread, and returns a run identifier that can be inspected later. This slice must replace the current UUID-only stub with a real run lifecycle entrypoint, while keeping the graph execution narrow enough to be reliable in dev.

This is not the full teaching-pack generator yet. The goal is a real, inspectable run thread that proves the gateway can create state, invoke the engine, persist enough metadata, and expose a stable run id for the rest of the flow.

## Acceptance criteria

- [ ] Authenticated `POST /run` accepts a lesson request and returns a schema-matching response containing `run_id`, `status`, and current state/progress metadata.
- [ ] The run is persisted in the gateway run store and survives a follow-up request within the same dev process.
- [ ] The initial state includes teacher id, raw request, class info, run id, defaults for artifact/export fields, and a LangGraph thread/config id.
- [ ] The gateway invokes the compiled graph or a deliberately bounded first graph step; it must not be a pure stub.
- [ ] Failures during run creation return structured error responses with `X-Request-ID`.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: state factory builds a complete `OhMyClassState` from a minimal run request.
- [ ] Unit: invalid/missing request fields are rejected by FastAPI/Pydantic with structured validation error.
- [ ] Integration: authenticated `POST /run` creates a persisted run and returns HTTP 200 with the expected response schema.
- [ ] Integration: unauthenticated `POST /run` returns 401/403 and does not create a run.
- [ ] Integration: graph invocation failure marks run as failed or returns a structured 500 without losing request id.
- [ ] Real surface: `curl` login or test token flow, then `curl POST /run`; capture response body and request id.
- [ ] Regression: existing gateway error-handler and request-id tests stay green.

## Blocked by

None - can start immediately
