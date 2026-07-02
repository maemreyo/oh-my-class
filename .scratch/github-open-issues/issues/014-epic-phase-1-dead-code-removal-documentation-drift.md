# Issue #14: [Epic][Phase 1] Dead-code removal & documentation drift

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/14
State: OPEN
Created: 2026-07-02T16:42:04Z
Updated: 2026-07-02T16:42:04Z
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

The codebase carries dead runtime code and documentation that no longer matches reality. This is the cheapest, lowest-risk work in the whole hardening effort and it clears the ground for the foundational phases. Removing it first means later state/harness/judge work is not confused by parked or abandoned surfaces.

This is a production-ready rebuild, NOT patching. Removals follow the repo precedent of big-bang physical deletion plus guard tests (see `test_no_legacy_runtime.py`), keeping the tree high-readability, SoC, modular and testable.

## Scope

Children of this epic (tracked as separate issues in this milestone):

- [ ] Delete Lead Agent + `task()` stub, add guard test.
- [ ] Delete the 8 PARKED_REACT middleware, renumber order, add guard test.
- [ ] Fix `AGENTS.md` documentation drift + add Parked-status TTL CI policy.

Coordination for this epic:

- [ ] Run these as the first phase — zero runtime risk, no dependency on state/judge/harness work.
- [ ] Confirm each child ships its own guard test so the removed surface cannot silently return.

## Acceptance

- [ ] All three child issues closed.
- [ ] Guard tests from each child pass in CI.
- [ ] No reference to Lead Agent or PARKED_REACT middleware remains in the live runtime.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`, `docs/adr/017-topic-decomposition-and-unit-fan-out.md`
- Verdict: `docs/reports/agents/01-dead-code-and-documentation-drift.md`, `docs/reports/agents/08-migration-roadmap.md`

## Depends on

- Phase 0 decisions locked (`[Epic][Phase 0] Product decisions locked`). See milestone `agents-hardening`.

