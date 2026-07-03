# Issue #13: [Epic][Phase 0] Product decisions locked — fast-lane + circuit-breaker (ADR-026/027)

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/13
State: OPEN
Created: 2026-07-02T16:42:01Z
Updated: 2026-07-02T16:42:01Z
Labels: enhancement, agents-refactor, phase-0
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Implementation Notes

- Confirmed ADR-026 exists and decides fast-lane Option A.
- Confirmed ADR-027 exists and decides layered per-provider/per-run Redis-backed circuit breakers.
- Updated `docs/reports/agents/ARCHITECTURE.md` INVARIANT-06 wording to match ADR-026.
- Updated `docs/reports/agents/08-migration-roadmap.md` so Phase 0 is marked complete and references ADR-026/027 as decided.
- Updated `docs/reports/agents/00-EXECUTIVE-SUMMARY.md` so the former contradiction is described as resolved by ADR-026, with implementation still tracked in later phases.

## Verification

- Targeted text check: confirmed `INVARIANT-06` now says "cannot be silently bypassed" in `ARCHITECTURE.md`.
- Surface QA: inspected the local markdown ticket and documentation text as rendered markdown source; links/paths are present and status is DONE.

## Body

## Context

Phase 0 blockers were the product-level decisions that everything else depends on. They have now been resolved through a grilling / decision session and captured as ADRs. Fast-lane teacher-gate behaviour and circuit-breaker scope are no longer open questions. This epic tracks closing out Phase 0 — which is essentially **done** except for one documentation-wording task.

This is a production-ready rebuild, NOT patching. Where code changes land in later phases, they follow the repo precedent of big-bang physical deletion plus guard tests (see `test_no_legacy_runtime.py`), with high readability, clear separation of concerns, and modular, testable design.

## Scope

- [ ] Confirm ADR-026 is merged: fast-lane teacher-gate **Option A**, auto-approve gated on `compliance_gate_node` passing.
- [ ] Confirm ADR-027 is merged: layered circuit breaker (per-provider + per-run), Redis-backed.
- [ ] Reword **INVARIANT-06** in `docs/reports/agents/ARCHITECTURE.md` to match ADR-026 (fast-lane is a conditional auto-approval, not a removal of the teacher gate). This is the only remaining code/doc task in Phase 0.

## Acceptance

- [ ] Both ADR-026 and ADR-027 are merged and referenced from the roadmap.
- [ ] INVARIANT-06 wording in `ARCHITECTURE.md` reflects the fast-lane semantics from ADR-026 and no longer contradicts it.

## References

- ADR: `docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`, `docs/adr/027-circuit-breaker-scope.md`
- Verdict / roadmap: `docs/reports/agents/08-migration-roadmap.md`, `docs/reports/agents/00-EXECUTIVE-SUMMARY.md`, `docs/reports/agents/ARCHITECTURE.md`

## Depends on

- Nothing — this is the root epic. All other phases assume these decisions are locked. See milestone `agents-hardening`.
