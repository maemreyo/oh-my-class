# Issue #26: [Phase 3] AgentRuntime shared harness + tool capability registry

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/26
State: OPEN
Created: 2026-07-02T16:42:44Z
Updated: 2026-07-02T16:42:44Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Progress notes

- Added `packages/agents/runtime.py` with shared `AgentRuntime` / `AgentRuntimeConfig` for the four production agents:
  - centralizes retry-attempt logging, temperature schedule, INVARIANT-07 tags, and the underlying streaming/transport selection already owned by `complete_json_chat`.
  - emits numeric `step:` plus human `stage:` tags so existing transport policy can parse step numbers while traces keep stage identity.
- Migrated production agent call paths to `AgentRuntime`:
  - `packages/agents/sub_agents/planner/nodes.py`
  - `packages/agents/sub_agents/researcher/nodes.py`
  - `packages/agents/sub_agents/content_creator/nodes.py`
  - `packages/agents/sub_agents/reviewer/nodes.py`
- Added `packages/agents/tools/capabilities.py` with `AGENT_CAPABILITIES`, `ToolStatus`, `ToolCapability`, and `bind_agent_tools()`.
- Added `packages/agents/tools/fs.py` as the single sandboxed read/write implementation with:
  - workspace path enforcement;
  - `ToolUnavailableError.fail_type == "tool_unavailable"` for forbidden/out-of-sandbox access;
  - in-memory write audit log via `write_audit_log()` / `clear_write_audit_log()`.
- Replaced legacy/stub FS surfaces with delegation to `tools/fs.py`:
  - `packages/agents/tools/read_file.py`
  - `packages/agents/tools/write_file.py`
  - `packages/agents/sub_agents/planner/tools.py`
  - `packages/agents/sub_agents/researcher/tools.py`
  - `packages/agents/sub_agents/content_creator/tools.py`
  - `packages/agents/sub_agents/reviewer/tools.py`
- Added guard/runtime tests:
  - `packages/agents/tests/test_agent_runtime_tools.py`
  - `packages/agents/tests/test_no_unimplemented_tool_bound.py`
- Updated existing content-creator tool tests to exercise workspace-sandboxed FS paths and the reviewer live-path test to patch the new shared runtime seam.

## Verification evidence

- `uv run pytest packages/agents/tests/test_agent_runtime_tools.py packages/agents/tests/test_no_unimplemented_tool_bound.py packages/agents/tests/sub_agents/test_content_creator.py packages/agents/tests/sub_agents/test_researcher.py packages/agents/tests/sub_agents/test_planner.py packages/agents/tests/test_no_legacy_judge_live_path.py packages/agents/tests/llm/test_production_provenance.py -q` → `98 passed`.
- Post-review remediation migrated auxiliary sub-agent LLM profiles onto `AgentRuntime`:
  - `packages/agents/sub_agents/diagnostician/nodes.py`
  - `packages/agents/sub_agents/roadmap_agent/nodes.py`
  - `packages/agents/sub_agents/practice_generator/semantic_anchor.py`
  - `packages/agents/sub_agents/content_creator/semantic_anchor_synthesis.py`
  - `packages/agents/sub_agents/researcher/lexical_grounding.py`
- Added `packages/agents/tests/test_no_sub_agent_runtime_bypass.py` to fail when sub-agent modules directly reference `complete_json_chat` instead of the shared runtime.
- `rg -n "complete_json_chat|compiled_json_chat|log_llm_start|log_llm_success|log_llm_failure" packages/agents/sub_agents -g "*.py"` → no prohibited live direct usage.
- `uv run pytest packages/agents/tests/test_agent_runtime_tools.py packages/agents/tests/test_no_unimplemented_tool_bound.py packages/agents/tests/test_no_sub_agent_runtime_bypass.py packages/agents/tests/sub_agents/test_content_creator.py packages/agents/tests/sub_agents/test_researcher.py packages/agents/tests/sub_agents/test_planner.py packages/agents/tests/test_no_legacy_judge_live_path.py packages/agents/tests/llm/test_production_provenance.py packages/agents/tests/sub_agents/test_diagnostician.py packages/agents/tests/sub_agents/test_roadmap_agent.py packages/agents/tests/test_practice_generator_semantic_anchor.py packages/agents/tests/test_semantic_anchor_synthesis.py packages/agents/tests/test_researcher_lexical_grounding.py -q` → `183 passed`.
- Post-review remediation centralized retry helpers in `AgentRuntime`:
  - `complete_json_with_retries(...)` for uncompiled JSON calls;
  - `complete_compiled_json_with_retries(...)` for prompt-compiler-backed calls.
- Planner, researcher, and content-creator manual retry loops now delegate through the shared runtime retry helpers while preserving their parse/retry-prompt semantics.
- Reviewer transport now preserves judge-supplied temperatures (`0.3`, `0.4`, `0.5`) and maps `judge:N` metadata to `attempt:N` runtime tags instead of hardcoding `attempt=0`.
- Added runtime regression coverage for explicit temperature preservation in `packages/agents/tests/test_agent_runtime_tools.py`.
- `uv run pytest packages/agents/tests/test_agent_runtime_tools.py packages/agents/tests/test_no_sub_agent_runtime_bypass.py packages/agents/tests/test_no_unimplemented_tool_bound.py packages/llm_client/tests/test_client.py services/gateway/tests/test_provider_circuit_breaker.py -q` → `22 passed`.
- Broader post-review focused suite covering runtime, bypass guards, sub-agent retry users, LLM breaker, worker observability, router, and gate registry → `147 passed`.
- LSP diagnostics clean for changed Issue #26 Python files checked:
  - `packages/agents/runtime.py`
  - `packages/agents/tools/fs.py`
  - `packages/agents/tools/capabilities.py`
  - `packages/agents/sub_agents/planner/nodes.py`
  - `packages/agents/sub_agents/researcher/nodes.py`
  - `packages/agents/sub_agents/content_creator/nodes.py`
  - `packages/agents/sub_agents/reviewer/nodes.py`
  - `packages/agents/tests/test_agent_runtime_tools.py`
  - `packages/agents/tests/test_no_unimplemented_tool_bound.py`
  - `packages/agents/sub_agents/diagnostician/nodes.py`
  - `packages/agents/sub_agents/roadmap_agent/nodes.py`
  - `packages/agents/sub_agents/practice_generator/semantic_anchor.py`
  - `packages/agents/sub_agents/content_creator/semantic_anchor_synthesis.py`
  - `packages/agents/sub_agents/researcher/lexical_grounding.py`
  - `packages/agents/tests/test_no_sub_agent_runtime_bypass.py`
  - `packages/agents/tests/test_researcher_lexical_grounding.py`
- Manual surface smoke through the runtime/tool API:
  - `AgentRuntime.tags()` returned agent/run/step/stage/attempt/task/pipeline metadata;
  - `bind_agent_tools("content_creator", ("read_file", "write_file"))` succeeded;
  - binding `task` raised `ToolUnavailableError` with `fail_type="tool_unavailable"`;
  - `write_file()` wrote `.scratch/issue-026-manual-smoke.txt`, `read_file()` read it back, and the audit log recorded path/bytes;
  - reading `/tmp/issue-026-outside.txt` raised `ToolUnavailableError` with `tool_name="fs"`.
- Post-review manual smoke through the async FS API again passed: `issue-026 manual smoke: PASS`.
- Pure LOC audit for post-review files returned all files below the 250 LOC ceiling; largest checked file was `176` pure LOC.
- The no-excuse helper referenced by the programming skill is not present at `scripts/python/check-no-excuse-rules.py`, so the available repo gates used here were focused pytest, LSP diagnostics, raw bypass search, manual smoke, and pure LOC measurement.
- Size audit performed on changed files; no new/modified Issue #26 file exceeded 250 pure LOC. Pre-existing large tests/modules remain outside this issue's scope.
- Round 2 remediation wired production sub-agent tool entrypoints through `bind_agent_tools(...)` for planner, researcher, content creator, and reviewer, so the capability registry is exercised by runtime-facing tool modules rather than only by tests over `AGENT_CAPABILITIES`.
- Round 2 guard: `packages/agents/tests/test_no_unimplemented_tool_bound.py::test_production_tool_entrypoints_call_capability_registry` fails if production tool entrypoints bypass the capability registry.
- Round 2 verification: `uv run pytest packages/agents/tests/test_no_unimplemented_tool_bound.py packages/agents/tests/test_agent_runtime_tools.py packages/agents/tests/sub_agents/test_content_creator.py::TestContentCreatorTools -q` → 12 passed.

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
