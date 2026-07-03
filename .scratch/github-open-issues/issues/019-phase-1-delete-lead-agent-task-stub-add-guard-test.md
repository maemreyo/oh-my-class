# Issue #19: [Phase 1] Delete Lead Agent + task() stub, add guard test

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/19
State: OPEN
Created: 2026-07-02T16:42:27Z
Updated: 2026-07-02T16:42:27Z
Labels: enhancement, agents-refactor, phase-1
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Implementation Notes

- Deleted `packages/agents/lead_agent/` and generated cache leftovers.
- Deleted `packages/agents/tools/task.py` and removed its package export.
- Deleted the old lead-agent tests under `packages/agents/tests/test_lead_agent.py`.
- Expanded `tests/test_no_lead_agent.py` so it fails if the Lead Agent directory, the task stub, or the old top-level lead-agent test returns.
- Removed `lead_agent` model assignment/config tests because the runtime surface is decommissioned.
- Removed lead-agent prompt/state references from related tests.

## Verification

- Red first: `uv run pytest tests/test_no_lead_agent.py` failed while the dead surfaces existed.
- Targeted tests: `uv run pytest tests/test_no_lead_agent.py packages/agents/config/tests/test_gate_config.py packages/agents/config/tests/test_model_tiering.py packages/agents/tests/test_llm_config.py packages/agents/tests/test_prompt_management.py packages/agents/tests/test_state_schemas.py` → 109 passed.
- Type check: `uv run basedpyright tests/test_no_lead_agent.py packages/agents/tools/__init__.py packages/agents/config/models.py packages/agents/config/model_drift.py packages/agents/config/tests/test_gate_config.py packages/agents/config/tests/test_model_tiering.py packages/agents/tests/test_llm_config.py packages/agents/tests/test_prompt_management.py packages/agents/tests/test_state_schemas.py` → 0 errors.
- LSP diagnostics: clean on changed Python files.
- Surface QA: imported `packages.agents.tools` and confirmed `task` is not exported; importing `packages.agents.lead_agent` and `packages.agents.tools.task` raises `ModuleNotFoundError`.

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
