# Issue #20: [Phase 1] Delete 8 PARKED_REACT middleware, renumber order, guard test

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/20
State: OPEN
Created: 2026-07-02T16:42:29Z
Updated: 2026-07-02T16:42:30Z
Labels: enhancement, agents-refactor, phase-1
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Implementation Notes

- Removed the `PARKED_REACT_MIDDLEWARE` registry surface.
- Removed the 8 parked ReAct-only middleware from `ORDERED_MIDDLEWARE_LIST`.
- Renumbered the active middleware chain to 23 contiguous layers.
- Kept `ClarificationMiddleware` last and updated its order to 23.
- Added `tests/test_no_parked_middleware_registered.py` to fail if the parked registry returns, parked middleware becomes active, or order continuity/last-clarification breaks.
- Updated middleware ordering tests to the new active chain.

## Verification

- Targeted tests: `uv run pytest packages/agents/tests/middleware/test_middleware_suite.py tests/test_no_parked_middleware_registered.py` → 12 passed.
- Type check: `uv run basedpyright packages/agents/middleware/registry.py packages/agents/middleware/base.py packages/agents/middleware/terminal/clarification.py packages/agents/tests/middleware/test_middleware_suite.py tests/test_no_parked_middleware_registered.py` → 0 errors.
- LSP diagnostics: clean on changed middleware/test Python files.
- Surface QA: imported `packages.agents.middleware` and observed count 23, orders 1-23, last middleware `clarification`, and no parked middleware active.
- Round 2 remediation physically deleted parked middleware/shim files and removed parked exports from middleware package `__init__.py` files; the guard now asserts those files are absent, not merely unregistered.
- Round 2 verification: `uv run pytest tests/test_no_parked_middleware_registered.py packages/agents/tests/test_no_legacy_judge_live_path.py packages/quality/tests/test_layer4_judge.py packages/quality/tests/test_judge_interface.py packages/agents/tests/middleware/test_middleware_suite.py -q` → 64 passed.

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
