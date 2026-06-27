---
title: Pipeline V2 control plane, executor, resume API, and status machine
status: ready-for-agent
labels: [pipeline-v2, gateway, executor, gates]
created: 2026-06-27
order: 3
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-002-production-persistence]
adr_refs:
  - docs/adr/005-generic-gate-resume-api.md
  - docs/adr/004-production-run-persistence.md
---

## Problem

Current `/run` and `/approve` requests execute graph work synchronously. Live approval requests can timeout while the graph continues, leaving stale or confusing run state. Pipeline V2 needs HTTP as control plane and background execution as execution plane.

## Scope

Implement the V2 control plane and executor.

Agent-ready tasks:

1. Add `POST /run` V2 behavior that persists a run and schedules execution, returning quickly.
2. Add `POST /run/{run_id}/resume` with gate registry validation.
3. Implement gate registry for `clarification_required`, `contract_confirmation`, `search_plan_confirmation`, `blueprint_approval`, and `content_approval`.
4. Implement queue/executor abstraction with production-ready semantics and an initial robust adapter suitable for the app runtime.
5. Implement explicit run status state machine with canonical writer in the executor.
6. Implement SSE replay from persisted events plus live streaming.
7. Ensure executor resumes LangGraph using `Command(resume=...)`.
8. Ensure failures persist status, event, and error summary.

## Out Of Scope

- Frontend gate shell implementation.
- Research Engine internals.
- Artifact generation internals.

## Acceptance Criteria

- `/run` does not hold the request open for long-running LLM work.
- `/resume` validates gate/action/payload before scheduling continuation.
- Status transitions are validated and persisted.
- SSE reconnect can replay missed events.
- Gateway restart does not lose run metadata or gate records.
- Existing user journey remains possible through updated V2 APIs.

## Test Plan

- Real Postgres integration tests for run creation, resume, status updates, and event replay.
- API tests for invalid gate, invalid action, stale gate, unauthorized teacher, and successful resume.
- Executor tests for success, failure, and cancellation/escalation paths.

## Observability

- Emit compact events for queued, started, stage started/completed, gate required, resumed, failed, and completed.
- Langfuse traces should include run id and stage but are not source of truth.

## Required Edge Cases And Tests

- Duplicate `POST /run` with the same idempotency key returns the same run response.
- Same idempotency key with a different request body is rejected.
- Double-click resume produces one accepted gate response and one idempotent response or conflict.
- Resume with stale gate id/version returns `409` and current gate/status.
- Resume by a non-owner teacher is rejected.
- Resume by school admin is allowed only within organization.
- Worker crash before stage start, during stage, and after stage completion is recoverable.
- Expired job lease can be reclaimed without duplicating completed stage side effects.
- SSE reconnect with `last_event_id` replays missed events exactly once and then streams live events.
- Create/resume HTTP handlers return quickly and do not await long LLM work.
- Cancellation during queued, running, awaiting gate, and failed states has deterministic status transitions.
- Gate timeout never auto-approves; it escalates/notifies.
- Executor handles DB unavailable, 9Router unavailable, and Langfuse unavailable with correct failure/degradation semantics.

## Rollback

Disable V2 route wiring before user cutover if executor or resume behavior is unstable.
