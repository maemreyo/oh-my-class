---
title: Pipeline V2 production Postgres persistence
status: review-partial
labels: [pipeline-v2, persistence, postgres]
created: 2026-06-27
order: 2
blocked_by: [ISSUE-001-foundation-architecture]
adr_refs:
  - docs/adr/004-production-run-persistence.md
---

## Problem

Production Pipeline V2 cannot use in-memory run state. It needs durable run metadata, status history, contract revisions, gate records, artifact workflow state, rendered snapshots, persisted events, and LangGraph checkpointing.

## Scope

Implement production persistence using Postgres as source of truth.

Agent-ready tasks:

1. Design and add migrations for `runs`, `run_status_history`, `run_contracts`, `contract_revisions`, `gate_interrupts`, `gate_responses`, `artifact_workflows`, `artifact_snapshots`, and `run_events`.
2. Implement Run Store with CRUD/query methods for dashboard and executor.
3. Implement Status History writer and state transition audit.
4. Implement Gate Store for current interrupt and responses.
5. Implement Artifact Snapshot Store backed by Postgres, with object-store-ready interface.
6. Implement Event Store with sequence numbers, visibility levels, and replay query by `last_event_id`.
7. Wire LangGraph Postgres checkpointer for V2 thread id = run id.
8. Remove production dependency on in-memory `app.state.runs` for V2.

## Out Of Scope

- External object storage adapter.
- UI changes beyond API compatibility support.
- Research/generation behavior.

## Acceptance Criteria

- A V2 run can be created and read back after process restart.
- Status transitions are persisted with history.
- Events are persisted and replayable by sequence.
- Artifact snapshots store JSON and rendered HTML with hashes and version metadata.
- LangGraph checkpointing uses Postgres.
- Langfuse is not required for run recovery.

## Test Plan

- Real Postgres integration tests for migrations and stores.
- Test event replay ordering and visibility filtering.
- Test artifact snapshot hash uniqueness and retrieval.
- Test process-restart style recovery at store level.

## Observability

- Persist compact audit events for run creation, status change, gate interrupt, gate response, snapshot creation, and failure.
- Do not store raw prompts, raw fetched pages, secrets, or huge payloads in event rows.

## Required Edge Cases And Tests

- Alembic upgrade from an empty database succeeds.
- Alembic upgrade is idempotent in a clean test environment.
- Required indexes and uniqueness constraints exist for run id, event sequence, snapshot hashes, idempotency keys, and active gate state.
- Foreign-key cascades/restrictions match deletion and retention policy.
- Run store rejects cross-tenant reads and writes.
- Event sequence remains monotonic under concurrent event writes.
- Snapshot store deduplicates identical content/hash and rejects hash mismatches.
- Large but valid rendered HTML snapshots round-trip without truncation.
- Soft-deleted runs immediately deny artifact and gate access.
- Checkpointer state can resume after process restart.
- Langfuse outage does not affect persistence writes.
- DB transaction rollback leaves no half-created run, gate, event, or snapshot record.
- Tests cover unique violations, stale updates, missing rows, and serialization of every persisted JSON payload.

## Rollback

Database migrations should be forward-safe. If rollback is needed before cutover, disable V2 routes and leave V1 untouched until V2 persistence is stable.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Persistence primitives are broadly implemented, but the report overstates production-readiness proof.

Active-surface reconciliation: the historical review below names `pipeline_v2_*` files. The active persistence surface is `services/gateway/teaching_pack_store.py`, `teaching_pack_control_store.py`, `teaching_pack_job_store.py`, `teaching_pack_snapshot_store.py`, `teaching_pack_models.py`, `teaching_pack_snapshot_models.py`, and the active Teaching Pack graph/checkpointer wiring. New work must use those Teaching Pack files.

Evidence:
- Alembic migrations add Pipeline V2 persistence tables in `services/gateway/alembic/versions/002_pipeline_v2_persistence.py`, `003_pipeline_v2_control_tables.py`, `004_pipeline_v2_run_jobs.py`, `005_artifact_workflow_state.py`, `006_rendered_snapshot_metadata.py`, `007_soft_delete_and_retention.py`, `008_notifications.py`, and `009_release_evidence.py`.
- Run/event storage is implemented in `services/gateway/pipeline_v2_store.py`; snapshot storage in `services/gateway/pipeline_v2_snapshot_store.py`; gate/contract/workflow persistence in `services/gateway/pipeline_v2_control_store.py`.
- Postgres checkpointer wiring exists in `packages/agents/pipeline_v2/checkpointing.py`.
- Tests cover stores and persistence paths in `services/gateway/tests/test_pipeline_v2_store.py`, `test_pipeline_v2_control_store.py`, `test_pipeline_v2_snapshot_store.py`, `test_artifact_workflow_persistence.py`, and `packages/agents/tests/pipeline_v2/test_checkpointing.py`.

Gaps:
- I found store-level and integration-style tests, but not a real process-restart recovery proof for the full graph/checkpointer path.
- The staged evidence proves schema/store behavior, not full production recovery under deployed multi-process conditions.
