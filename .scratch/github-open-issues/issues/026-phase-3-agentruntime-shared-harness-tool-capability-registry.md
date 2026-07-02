# Issue #26: [Phase 3] AgentRuntime shared harness + tool capability registry

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/26
State: OPEN
Created: 2026-07-02T16:42:44Z
Updated: 2026-07-02T16:42:44Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

Each of the 4 agents carries its own ad-hoc harness — retry, backoff, temperature schedule, cost/metadata tagging, streaming selection — with no shared implementation. Tooling is also inconsistent and partly broken: `tools/read_file.py`, `tools/write_file.py`, and `tools/task.py` are ALL stubs raising `NotImplementedError` (docs wrongly claimed read/write were implemented); the real FS logic actually lives in `sub_agents/*/tools.py`. Harness unification must reconcile these.

This is a production-ready rebuild, NOT patching: extract one `AgentRuntime`, unify FS tools into a sandbox, and add guard tests preventing unimplemented tools from being bound. Enforce INVARIANT-07 cost/metadata tagging. High-readability, SoC, modular, testable.

## Scope

- [ ] Extract a shared `AgentRuntime` used by all 4 agents: retry + backoff, temperature schedule, cost/metadata tagging (per INVARIANT-07), and streaming selection.
- [ ] Add an `AGENT_CAPABILITIES` registry describing which tools each agent may bind, with an IMPLEMENTED status per tool.
- [ ] Add `test_no_unimplemented_tool_bound.py`: fails if any tool that is not IMPLEMENTED is bound to any LLM.
- [ ] Unify `read_file`/`write_file` into a single `tools/fs.py` sandbox (reconciling the stubs vs the real `sub_agents/*/tools.py` logic), with a write **audit log**.
- [ ] Add a `tool_unavailable` `fail_type` so calls to unimplemented/forbidden tools fail closed with a typed reason.

## Acceptance

- [ ] All 4 agents run through the single `AgentRuntime`; cost/metadata tagged per INVARIANT-07 (tested).
- [ ] `test_no_unimplemented_tool_bound.py` passes and catches a deliberately-bound stub.
- [ ] `tools/fs.py` is the only FS path; writes appear in the audit log; `task.py`/legacy stubs no longer bound.
- [ ] `tool_unavailable` fail_type is emitted for forbidden/unimplemented tool calls.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/04-agent-harness-tool-contracts.md`

## Depends on

- `[Epic][Phase 3] Core correctness` (parent) and Phase 2 state unify. Feeds Phase 4 resilience (breaker/fallback hang off `AgentRuntime`) and the RFC new-agents. See milestone `agents-hardening`.

