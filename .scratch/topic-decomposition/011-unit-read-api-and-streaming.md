---
title: Unit aggregate read API, multiplexed SSE, and unit actions
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Expose the backend↔frontend contract for the unit dashboard (ADR-017 §BE↔FE). One read model hydrates the dashboard; one multiplexed stream delivers live deltas; unit-level actions get their own endpoints while per-session actions reuse the existing resume endpoint.

`services/gateway/routers/unit_runs.py`:

- `GET /units/{id}` → `UnitView` (issue 001): parent meta + sequence + per-session status/progress + computed aggregate + coherence warnings + `cursor`. Status is computed from children at read time.
- `GET /units/{id}/status` (SSE) → multiplexes parent + child events filtered by `parent_run_id`, each tagged `session_index`, each carrying the monotonic `cursor`. Events are coarse session-level (`unit.session.status_changed`, `unit.session.ready_for_review`, `unit.progress`, `unit.coherence_warning`, `unit.theme_locked`, `unit.completed`, `unit.partially_complete`). Granular per-session steps stay on the existing `/runs/{child}/status` stream for drill-down.
- Unit actions: `POST /units/{id}/approve-all`, `POST /units/{id}/sessions/{session_id}/spawn-anyway`, `POST /units/{id}/export`. Per-session approve/reject/retry reuse `POST /runs/{child_run_id}/resume`.
- Aggregate counters in `unit.progress` are computed by the backend; the frontend never derives counts.

## Acceptance criteria

- [ ] `GET /units/{id}` returns a `UnitView` with computed status and a `cursor`; ownership is enforced (teacher owns parent + children).
- [ ] `GET /units/{id}/status` streams only that unit's events (filtered by `parent_run_id`), tagged with `session_index` and `cursor`, at coarse session granularity.
- [ ] Reconnect/gap handling: clients re-`GET` the snapshot and resume deltas with `cursor > snapshot.cursor`; deltas are self-sufficient and idempotent (last-writer-by-cursor per `session_id`).
- [ ] `approve-all` is **best-effort** and returns **per-child results** (which resumed, which failed) — not all-or-nothing; one failing child does not block the others. `spawn-anyway` force-spawns a blocked session; `export` triggers the unit packager (issue 017).
- [ ] Per-session actions reuse the existing resume endpoint unchanged. A session **rejected without feedback must not silently route to an empty export** (the pre-existing `route_after_teacher_approval` reject→`export_finalize` path): a rejected session regenerates or stays `in_review`, and the unit never counts an empty pack as `approved`/`complete`.
- [ ] `unit.progress` counters originate from the backend; the SSE stream uses `teaching_pack_event_bus` (runtime-parity issue 003) for delta delivery **only** — never a source of truth (read model + durable store are authoritative).

## Detailed test suite

(Real DB + real gateway app; real run/child rows.)

- [ ] `services/gateway/tests/test_unit_read_api.py`: `GET /units/{id}` returns counts and per-session statuses matching the underlying children; cross-teacher access is denied.
- [ ] `services/gateway/tests/test_unit_stream.py`: a child status change emits exactly one `unit.session.status_changed` on the unit stream with correct `session_index` and increasing `cursor`; events for other units are not leaked.
- [ ] `services/gateway/tests/test_unit_stream.py`: a client that connects, drops, and reconnects re-snapshots and applies only `cursor`-newer deltas without double-counting.
- [ ] `services/gateway/tests/test_unit_actions.py`: `approve-all` returns per-child results and resumes the succeeding children even when one child resume fails; `spawn-anyway` unblocks a session; per-session `resume` still works via `/runs/{child}/resume`.
- [ ] `scripts/verify_frontend_api_contracts.py` passes for the new endpoints.
- [ ] Run `uv run pytest services/gateway/tests/test_unit_read_api.py services/gateway/tests/test_unit_stream.py services/gateway/tests/test_unit_actions.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
- .scratch/topic-decomposition/010-unit-orchestrator.md
