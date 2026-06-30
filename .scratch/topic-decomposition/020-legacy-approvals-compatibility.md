---
title: Legacy /run/approvals compatibility and deprecation
status: done
labels: []
created: 2026-06-30
---

## What to build

Prevent the legacy approval route from mishandling unit gates, and converge all teaching-pack gate actions on one path (ADR-017 §Gating; review blocking gap #2).

`services/gateway/routers/approvals.py` currently hardcodes `_VALID_GATES = {"blueprint_approval", "content_approval"}` and `ApprovalAction` only supports approve/reject (no `edit`). The authoritative path is `POST /teaching-packs/runs/{id}/resume` + `teaching_pack_gate_registry`.

- All teaching-pack gate actions — including `unit_approval` and `edit` — go exclusively through the teaching-pack resume endpoint + gate registry.
- The legacy `/run/approvals` route is **frozen** (not extended) and made **fail-closed**: any gate name outside its known set is rejected with a clear error, so a unit gate can never be approved/bypassed through it.
- Mark the route deprecated with a removal plan once no consumer remains (confirm no frontend usage).

## Acceptance criteria

- [x] `unit_approval` and `edit` are handled only via `/teaching-packs/runs/{id}/resume` + `teaching_pack_gate_registry`; the legacy route is never a path for them.
- [x] `/run/approvals` rejects any unknown/unsupported gate name fail-closed (no silent mishandling, no bypass of the registry).
- [x] The route is decommissioned with HTTP 410; no frontend code calls it.

## Detailed test suite

(Real gateway app + real DB.)

- [x] Existing legacy approvals route returns `410 Gone`, so unit gates cannot be accepted there.
- [x] `edit` is not accepted by the legacy `ApprovalAction` enum and the route is decommissioned.
- [x] `unit_approval` approve/reject/edit succeed through `teaching_pack_gate_registry` validation.
- [x] Consumer check: dashboard links use teaching-pack flows and no unit path references `/run/approvals`.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
