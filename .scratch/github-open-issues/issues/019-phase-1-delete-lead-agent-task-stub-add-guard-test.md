# Issue #19: [Phase 1] Delete Lead Agent + task() stub, add guard test

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/19
State: OPEN
Created: 2026-07-02T16:42:27Z
Updated: 2026-07-02T16:42:27Z
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

The Lead Agent is dead runtime. The actual runtime is the Teaching-Pack Stage Graph, yet the Lead Agent code and its `task()` stub still live in the tree, inviting confusion and accidental re-wiring. Files still present: `packages/agents/lead_agent/{config,recovery,tools}.py`, `packages/agents/lead_agent/prompts/system.md`, `packages/agents/lead_agent/__init__.py`, `packages/agents/lead_agent/tests/`, plus `tests/test_lead_agent.py`. `tools/task.py` is a stub raising `NotImplementedError`.

This is a production-ready rebuild, NOT patching: physically delete the dead surface big-bang and lock it out with a guard test, following the repo precedent `test_no_legacy_runtime.py`. High-readability, SoC, modular, testable.

## Scope

- [ ] Delete `packages/agents/lead_agent/` entirely (`config.py`, `recovery.py`, `tools.py`, `prompts/system.md`, `__init__.py`, `tests/`).
- [ ] Delete the `task()` definition / `tools/task.py` stub and remove any imports/bindings of it.
- [ ] Remove `tests/test_lead_agent.py`.
- [ ] Add `test_no_lead_agent_runtime.py`, copying the pattern from `test_no_legacy_runtime.py`, that fails if any `lead_agent` module or `task()` symbol is importable/registered.

## Acceptance

- [ ] `test_no_lead_agent_runtime.py` passes and would fail if the Lead Agent or `task()` returned.
- [ ] Repo-wide search shows no live import of `lead_agent` or `task`.
- [ ] Full test suite green after deletion.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/01-dead-code-and-documentation-drift.md`

## Depends on

- `[Epic][Phase 1] Dead-code removal & documentation drift` (parent). No code dependency on other issues. See milestone `agents-hardening`.

