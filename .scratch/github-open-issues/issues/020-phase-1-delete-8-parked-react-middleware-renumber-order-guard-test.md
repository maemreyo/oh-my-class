# Issue #20: [Phase 1] Delete 8 PARKED_REACT middleware, renumber order, guard test

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/20
State: OPEN
Created: 2026-07-02T16:42:29Z
Updated: 2026-07-02T16:42:30Z
Labels: enhancement, agents-refactor, phase-1
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

The middleware registry carries a `PARKED_REACT_MIDDLEWARE` dict of 8 parked middleware at `packages/agents/middleware/registry.py:108`. They are not wired into the active runtime but they pollute the registry, muddy the ordering, and risk accidental activation. Removing them tightens the active middleware chain.

Constraint: the Clarification middleware must remain **last** per INVARIANT-08.

This is a production-ready rebuild, NOT patching: delete the parked dict big-bang, renumber the active order contiguously, and add a guard test — repo precedent `test_no_legacy_runtime.py`. High-readability, SoC, modular, testable.

## Scope

- [ ] Remove the `PARKED_REACT_MIDDLEWARE` dict at `packages/agents/middleware/registry.py:108` (all 8 entries).
- [ ] Renumber the active middleware order values so they are contiguous with no gaps.
- [ ] Keep Clarification middleware last (INVARIANT-08).
- [ ] Add `test_no_parked_middleware_registered.py` that fails if any parked/PARKED_REACT middleware is present in the active registry.

## Acceptance

- [ ] `test_no_parked_middleware_registered.py` passes.
- [ ] Active middleware ordering is contiguous and Clarification is verified last (INVARIANT-08 test still green).
- [ ] No reference to `PARKED_REACT_MIDDLEWARE` remains.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/01-dead-code-and-documentation-drift.md`

## Depends on

- `[Epic][Phase 1] Dead-code removal & documentation drift` (parent). Independent of other issues. See milestone `agents-hardening`.

