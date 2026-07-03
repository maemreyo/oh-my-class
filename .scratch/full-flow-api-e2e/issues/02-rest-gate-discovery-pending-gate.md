# [FFA-02] REST gate discovery — `pending_gate` on GET /runs/{id}

Status: DONE
Labels: full-flow-api, gateway
ADR: 028
Depends on: none (foundational)

## Context

`GET /teaching-packs/runs/{id}` returns `{run_id, status, raw_request, artifact_statuses}`
only (`services/gateway/routers/teaching_pack_schemas.py`) — no gate fields. The pending
`gate_id`/`snapshot_ids` are emitted ONLY via SSE `*.opened` events
(`teaching_pack_completion.py`), but `POST .../resume` requires `gate_id`+`gate_name`
(`teaching_pack_runs.py:143-278`). So a pure-REST client cannot resume a gate. Blocks
"operate the whole flow via API" and the FFA-10 driver.

## Scope

- [x] Add `pending_gate: {gate_id, gate_name, allowed_actions, snapshot_ids} | null` to
      `TeachingPackRunStatusResponse` and the `GET /runs/{id}` handler
      (`teaching_pack_lifecycle.py`).
- [x] Source `allowed_actions` from `allowed_actions_for_gate`
      (`teaching_pack_gate_registry.py`) — single source of truth, no client hardcoding.
- [x] Populate from the currently-open gate (control store); `null` when none open.
- [x] Keep SSE `/status` unchanged (additive, backward-compatible).
- [x] Document the REST poll-drive loop in `docs/observability.md` or API docs.

## Acceptance

- Contract test: `pending_gate` is populated while `status == awaiting_approval` and `null`
  otherwise; `allowed_actions` matches the registry for `content_approval`.
- A REST-only client can: create → poll `GET /runs/{id}` until `pending_gate != null` →
  `POST resume` with that `gate_id`/`gate_name` → succeeds.
- Existing SSE consumers + web dashboard unaffected.

## References

- ADR-028. `teaching_pack_runs.py:143-278`, `teaching_pack_schemas.py`,
  `teaching_pack_gate_registry.py` (allowed_actions_for_gate), `teaching_pack_completion.py`.
