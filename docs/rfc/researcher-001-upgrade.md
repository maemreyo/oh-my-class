# RFC: Researcher agent upgrade (`researcher-001`)

Status: Proposed  
Owner: agents  
Depends on: ADR-018 runtime parity, Issue #26 `AgentRuntime`, Issue #23 observability backbone

## Context

The upgraded Researcher agent must build on the shared `AgentRuntime` instead of a bespoke LLM harness. The repo does not contain an external `researcher-001` recommendation file, so this RFC records the source recommendation set as the canonical local spec.

## Recommendation set

- Use `AgentRuntime` for retries, attempt tags, model selection, and cost attribution.
- Declare tools through `AGENT_CAPABILITIES`; bind only implemented capabilities.
- Emit research provenance as structured JSON: sources, claim map, verification status, and uncertainty notes.
- Keep FACT protocol as the boundary: every high-risk factual claim needs at least two independent sources before it becomes `VERIFIED`.
- Route live LLM calls through 9Router model `4omc` on `:20228` for real-LLM acceptance.

## Interface

Input stays the teaching-pack state slice:

- `raw_request`
- `lesson_plan`
- `research_policy`
- `class_info`
- `run_id`

Output remains `ResearchBundle` in `common/contracts`, extended only if the contract lacks fields for claim-level provenance.

## Runtime design

The node constructs `AgentRuntimeConfig(agent="researcher", run_id, step, step_label, model="4omc")` and calls runtime retry helpers. Retry prompts include the parse error and the previous invalid output. The node must not call LiteLLM/OpenAI directly.

## Tool capabilities

Required capabilities:

- `web_search`
- `web_fetch`
- `read_file`

The capability registry rejects `task`, `write_file`, or unimplemented placeholders for this agent.

## Acceptance tests

- Contract test: output validates as `ResearchBundle` and includes source provenance.
- Guard test: no direct LLM transport is imported from the Researcher node.
- Real-LLM test: 9Router `:20228`, model `4omc`, standard research policy, at least five sources for `standard`.
- Safety test: high-risk factual claim without two sources is tagged `UNCERTAIN`, not `VERIFIED`.
