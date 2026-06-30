---
title: Legacy /run/approvals compatibility and deprecation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Prevent the legacy approval route from mishandling unit gates, and converge all teaching-pack gate actions on one path (ADR-017 §Gating; review blocking gap #2).

`services/gateway/routers/approvals.py` currently hardcodes `_VALID_GATES = {"blueprint_approval", "content_approval"}` and `ApprovalAction` only supports approve/reject (no `edit`). The authoritative path is `POST /teaching-packs/runs/{id}/resume` + `teaching_pack_gate_registry`.

- All teaching-pack gate actions — including `unit_approval` and `edit` — go exclusively through the teaching-pack resume endpoint + gate registry.
- The legacy `/run/approvals` route is **frozen** (not extended) and made **fail-closed**: any gate name outside its known set is rejected with a clear error, so a unit gate can never be approved/bypassed through it.
- Mark the route deprecated with a removal plan once no consumer remains (confirm no frontend usage).

## Acceptance criteria

- [ ] `unit_approval` and `edit` are handled only via `/teaching-packs/runs/{id}/resume` + `teaching_pack_gate_registry`; the legacy route is never a path for them.
- [ ] `/run/approvals` rejects any unknown/unsupported gate name fail-closed (no silent mishandling, no bypass of the registry).
- [ ] The route is annotated deprecated; a follow-up removal is documented; no frontend code calls it.

## Detailed test suite

(Real gateway app + real DB.)

- [ ] `services/gateway/tests/test_legacy_approvals_failclosed.py`: posting `unit_approval` (or any non-`{blueprint,content}` gate) to `/run/approvals` is rejected with a 4xx and does not mutate run state.
- [ ] same file: posting `edit` to `/run/approvals` is rejected (it only supports approve/reject).
- [ ] `services/gateway/tests/test_unit_gate_resume_path.py`: `unit_approval` approve/reject/edit succeed via `/teaching-packs/runs/{id}/resume`.
- [ ] Consumer check: a grep/test asserts no frontend code references `/run/approvals` for teaching-pack gates.
- [ ] Run `uv run pytest services/gateway/tests/test_legacy_approvals_failclosed.py services/gateway/tests/test_unit_gate_resume_path.py -v`.

## Blocked by

- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
