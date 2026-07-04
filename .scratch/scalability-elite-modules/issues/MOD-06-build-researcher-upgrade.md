# [MOD-06] Build Researcher-upgrade module on AgentRuntime + Module Standard

Status: TODO
Labels: module-standard, agents, researcher
ADR: 033
Depends on: MOD-01, MOD-02

## Context

Build the upgraded Researcher agent per `docs/rfc/researcher-001-upgrade.md` as a Specialized
Module conforming to the ADR-033 6-point standard. The researcher sub-agent already exists
(`packages/agents/sub_agents/researcher/` — `nodes.py`, `runtime_grounding.py`, `tools.py`,
`triangulation.py`) and has an `AGENT_CAPABILITIES` entry
(`packages/agents/tools/capabilities.py:28-34`: `web_search`, `web_fetch`, `read_file`
IMPLEMENTED; `write_file` FORBIDDEN; `task` UNIMPLEMENTED). This issue brings it fully onto
`AgentRuntime` and the Module Standard, not a rewrite from zero.

## Scope

- [ ] Route all LLM calls through `AgentRuntime`
      (`AgentRuntimeConfig(agent="researcher", …, model="4omc")`); remove any direct
      LiteLLM/OpenAI transport from the researcher node (RFC "Runtime design").
- [ ] Contract: output validates as `ResearchBundle` in `common/contracts`, extended only if
      it lacks claim-level provenance fields (sources, claim map, verification status,
      uncertainty). Ensure Pydantic↔Zod parity if a Zod counterpart exists.
- [ ] Capabilities (MOD-01 point 2): keep the existing binding; assert `task`/`write_file` are
      never bound (RFC "Tool capabilities").
- [ ] Observability (point 4): emit `step_started`/`step_completed`/`step_failed`.
- [ ] Fail-closed (point 5): FACT protocol at the boundary — a high-risk claim without two
      independent sources is tagged `UNCERTAIN`, never `VERIFIED`. Run under the MOD-05 fault
      boundary.
- [ ] Manifest/version entry (point 6): register in the MOD-03 unified index.
- [ ] Tests (point 3): contract + guard (no direct transport) + live-path + real-LLM (9Router
      `:20228`, model `4omc`, ≥5 sources for `standard` policy) + safety test.

## Acceptance

- All acceptance tests in `docs/rfc/researcher-001-upgrade.md` pass.
- MOD-01 conformance test passes for `researcher`; MOD-03 drift shows it registered with
  contract + tests + reachable.
- Guard test proves no direct LLM transport import from the researcher node.
- Real-LLM test returns ≥5 sources for a standard research policy; a single-source high-risk
  claim is `UNCERTAIN`.

## References

- RFC: `docs/rfc/researcher-001-upgrade.md`
- `packages/agents/sub_agents/researcher/{nodes.py,runtime_grounding.py,triangulation.py}`
- `packages/agents/tools/capabilities.py:28-34, 48-58`
- `packages/agents/runtime.py:34-49`
- MOD-01 spec, MOD-05 fault boundary

## Implementation notes

- Use the MOD-02 scaffolder only for any missing compliant scaffolding (tests/observability
  stubs); the core node already exists — upgrade in place, production-ready.
- Reuse existing triangulation/grounding code; the change is transport + provenance +
  conformance, not the research logic.
