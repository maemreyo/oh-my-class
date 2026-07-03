# Issue #21: [Phase 1] Fix AGENTS.md drift + Parked-status TTL CI policy

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/21
State: OPEN
Created: 2026-07-02T16:42:32Z
Updated: 2026-07-02T16:42:32Z
Labels: enhancement, agents-refactor, phase-1
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Implementation Notes

- Rewrote `AGENTS.md` runtime overview so the Teaching-Pack Stage Graph is the authoritative runtime.
- Removed Lead-Agent-as-runtime sections, model assignment, legacy graph runtime details, and stale project-structure entries.
- Updated active middleware documentation to 23 layers with Clarification last at order 23.
- Added the Parked-status TTL policy to `AGENTS.md`, including the marker location and required fields.
- Added `tests/test_parked_status_ttl.py` with live repository scanning and fixtures that prove expired/missing TTL cases are detected.
- Added intentionally expired and missing-date fixtures under `tests/fixtures/parked_status_ttl/`.
- Added an explicit CI step for `pytest tests/test_parked_status_ttl.py --tb=short` before the full Python test run.

## Verification

- Targeted tests: `uv run pytest tests/test_parked_status_ttl.py` → 3 passed.
- Type check: `uv run basedpyright tests/test_parked_status_ttl.py` → 0 errors.
- LSP diagnostics: clean for `tests/test_parked_status_ttl.py` and `.github/workflows/ci.yml`.
- Text check: `AGENTS.md` no longer contains active-runtime claims for the Lead Agent, legacy graph, 24-layer middleware, or order-31 clarification.
- Surface QA: directly invoked the TTL checker on the expired fixture and observed `expired_component.md` reported as `expired on 2000-01-01`.

## Body

## Context

`AGENTS.md` still describes the runtime as being driven by the Lead Agent. That is drift: the real runtime is the **Teaching-Pack Stage Graph**. Separately, "Parked" components have no expiry — parked code lives forever, which is how the Lead Agent and PARKED_REACT middleware accumulated in the first place. We need a CI policy that forces parked components to expire.

This is a production-ready rebuild of the docs + policy, NOT patching. High-readability, SoC, testable (the TTL policy is itself enforced by CI).

## Scope

- [ ] Rewrite the runtime description in `AGENTS.md` so it documents the Teaching-Pack Stage Graph as the runtime (not the Lead Agent). Remove all Lead-Agent-as-runtime language.
- [ ] Add a CI "Parked-status TTL" policy: any component marked Parked carries a date; if it exceeds the TTL (e.g. 90 days) CI fails, forcing a decision to delete or un-park.
- [ ] Document where the Parked marker + date live and how the TTL is checked.

## Acceptance

- [ ] `AGENTS.md` describes the Stage Graph runtime with no Lead-Agent-as-runtime claims.
- [ ] CI job fails when a Parked component exceeds its TTL (verified with a fixture that is intentionally expired).

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/01-dead-code-and-documentation-drift.md`

## Depends on

- `[Epic][Phase 1] Dead-code removal & documentation drift` (parent). Best done after the Lead Agent and PARKED_REACT deletions so the docs describe the final state. See milestone `agents-hardening`.
