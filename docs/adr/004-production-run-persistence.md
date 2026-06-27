# ADR-004: Production Run Persistence

## Status

**Decided** (2026-06-27) — Pipeline V2 uses Postgres as the production source of truth. In-memory run state is not part of the production path.

## Context

The current gateway stores runs in `app.state.runs`, while LangGraph checkpointing handles graph state. Live approval requests can time out while the graph continues, leaving API-visible status stale or confusing. Pipeline V2 needs reliable run status, event replay, gate state, contract revisions, artifact workflow, snapshots, and resumability.

Langfuse is useful for traces, but it is not a workflow database.

## Decision

Use separate persistence responsibilities:

1. **Postgres Run Store** — canonical source of truth for product state.
   - `runs`
   - `run_status_history`
   - `run_contracts`
   - `contract_revisions`
   - `gate_interrupts`
   - `gate_responses`
   - `artifact_workflows`
   - `artifact_snapshots`
   - `run_events`

2. **LangGraph Postgres Checkpointer** — execution checkpoint/resume state with `thread_id = run_id`.

3. **Postgres-backed Artifact Snapshot Store** — immutable rendered HTML snapshots and content JSON snapshots by artifact/content hash. Keep an interface ready for future object storage.

4. **Langfuse** — observability only. It stores summaries, hashes, latency, error types, model metadata, and trace correlation. It is not required to resume a run.

Run events are persisted with sequence numbers and visibility levels:

- `teacher` for status, gate, artifact progress, preview ready, completion, failure;
- `admin` for retries, healing, source failures, model latency summaries;
- `internal` for compact technical breadcrumbs.

SSE replays missed events from Postgres using `last_event_id`, then streams live events.

## Consequences

- Production no longer depends on in-memory run state.
- Refresh/reconnect shows accurate progress.
- Background workers can update canonical status.
- Run and artifact approval can be audited.
- Langfuse downtime degrades observability but does not stop workflow execution.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep in-memory run store | Fast to implement | Not production-safe; loses state on restart |
| Use Langfuse as state store | Already integrated | Wrong responsibility; not resumable workflow source of truth |
| Store metadata in Postgres and HTML in S3 from day one | Scales larger artifacts | More moving parts for initial V2 |
| Postgres snapshots first with storage interface | Production-ready and simple | May need object store adapter later |
