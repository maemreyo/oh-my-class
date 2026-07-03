# ADR-028: Full REST Operability for Teaching-Pack Runs

## Status

**Proposed** (2026-07-03) — To drive a teaching-pack run entirely over the REST API (create → discover gate → resume → fetch output), the run status endpoint must expose the currently-open gate. Today `gate_id`/`snapshot_ids` are delivered **only** through the SSE `/status` stream, so any non-SSE client (headless driver, test harness, third-party integration) cannot resume a gate. This ADR adds REST gate discovery. Companion to ADR-029 (escalation) and ADR-030 (artifact coverage); enables the teacher-scenario e2e driver.

## Context

Verified against code (2026-07-03):
- `GET /teaching-packs/runs/{id}` → `TeachingPackRunStatusResponse` returns `{run_id, status, raw_request, artifact_statuses}` only — **no gate fields** (`services/gateway/routers/teaching_pack_schemas.py`).
- The pending gate's `gate_id` is emitted **only** in SSE `*.opened` events on `GET /teaching-packs/runs/{id}/status` (e.g. `teaching_pack.content_approval.opened` → `{gate_id, snapshot_ids, ...}`, `teaching_pack_completion.py`).
- `POST /teaching-packs/runs/{id}/resume` **requires** `gate_id` + `gate_name` (`teaching_pack_runs.py:143-278`).
- There is no endpoint to list open gates or a run's snapshot ids.

Consequence: a client that wants to poll-and-resume (the natural shape for scripts, CI, and the scenario driver) is forced to open and parse an SSE stream purely to obtain an id it then posts back. That is an integration hazard and blocks "operate the whole flow via API".

## Decision

### 1. Add `pending_gate` to the run status response

`GET /teaching-packs/runs/{id}` returns an additional field:

```json
{
  "run_id": "...",
  "status": "awaiting_approval",
  "raw_request": "...",
  "artifact_statuses": [ ... ],
  "pending_gate": {
    "gate_id": "gate-...",
    "gate_name": "content_approval",
    "allowed_actions": ["approve", "approve_selected", "reject", "reject_selected", "edit"],
    "snapshot_ids": ["snap-...", "snap-..."]
  }
}
```

`pending_gate` is `null` when no gate is open. `allowed_actions` is sourced from the single source of truth `allowed_actions_for_gate` (`teaching_pack_gate_registry.py`) so REST clients need not hardcode it. `snapshot_ids` mirror the `*.opened` event payload so a client can immediately fetch previews.

### 2. SSE remains the live channel; REST becomes sufficient for poll-drive

SSE `/status` is unchanged (live updates, teacher dashboard). REST gains parity for the discover→resume loop so a pure-REST client can: `create → poll GET /runs/{id} until pending_gate != null → POST resume → poll → fetch snapshots/exports`. No SSE dependency required.

### 3. Snapshot enumeration

`pending_gate.snapshot_ids` covers the content-approval case. Additionally document that per-artifact HTML is retrieved via `GET /teaching-packs/runs/{id}/snapshots/{snapshot_id}/preview?view=student|teacher` and metadata via `GET .../snapshots/{snapshot_id}`.

## Consequences

- The full run lifecycle becomes scriptable over plain REST — unblocks the teacher-scenario e2e driver and any headless integration.
- Additive, backward-compatible: existing SSE consumers and the web dashboard are unaffected (`pending_gate` is a new optional field).
- One new source of truth reused (`allowed_actions_for_gate`) — no duplicated action lists on the client.
- Must be covered by a contract test asserting `pending_gate` is populated while `status == awaiting_approval` and `null` otherwise.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Add `pending_gate` to `GET /runs/{id}` (chosen)** | REST self-sufficient; backward compatible; one round-trip | Slightly larger status payload |
| Dedicated `GET /runs/{id}/gate` endpoint | Cleaner SoC | Extra round-trip per poll; another route to secure/test |
| Keep SSE-only | No backend change | Every client must speak SSE just to get an id — blocks "API-operable" goal |
