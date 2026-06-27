# ADR-005: Generic Gate Resume API

## Status

**Decided** (2026-06-27) — Pipeline V2 uses a generic resume endpoint and a gate registry.

## Context

The current gateway has `/approve` and `/reject` endpoints hard-coded for `blueprint_approval` and `content_approval`. Pipeline V2 introduces more interrupt types: clarification, contract confirmation, search plan confirmation, blueprint approval, content approval, scoped artifact rejection, and later gates.

Hard-coding endpoints per gate would make the API and UI brittle.

## Decision

Introduce `POST /run/{run_id}/resume` as the primitive control-plane endpoint.

The request shape is gate-aware:

```json
{
  "gate": "contract_confirmation",
  "action": "confirm",
  "payload": {}
}
```

A backend gate registry validates:

- gate type;
- allowed actions;
- payload schema;
- current run status;
- teacher/admin authorization;
- whether the gate interrupt is current and resumable.

Initial V2 gates:

- `clarification_required`
  - actions: `answer`, `cancel`
- `contract_confirmation`
  - actions: `confirm`, `edit_contract`, `cancel`
- `search_plan_confirmation`
  - actions: `confirm`, `edit_search_plan`, `skip_search`, `cancel`
- `blueprint_approval`
  - actions: `approve`, `edit`, `reject`
- `content_approval`
  - actions: `approve`, `reject`, `request_changes`

The endpoint records the gate response in Postgres, then schedules a background continuation using LangGraph `Command(resume=...)`.

`/approve` and `/reject` compatibility wrappers are not required for V2 unless needed temporarily during frontend cutover.

## Consequences

- Gate behavior is extensible without adding endpoints.
- UI can use a single resume client with gate-specific body components.
- Resume is asynchronous: HTTP returns quickly and execution continues in the background.
- Gate responses are audit records, not transient request bodies.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep `/approve` and `/reject` only | Simple | Cannot express clarification, contract edit, or search confirmation |
| Endpoint per gate | Explicit | API surface grows quickly and duplicates validation |
| Generic `/resume` + gate registry | Flexible and testable | Requires registry schemas and UI mapping |
