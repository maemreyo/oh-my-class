# [MOD-09] Build Differentiation module on AgentRuntime + Module Standard

Status: TODO
Labels: module-standard, agents, quality, differentiation
ADR: 033
Depends on: MOD-01, MOD-02

## Context

Build the Differentiation module per `docs/rfc/differentiation-module.md` as a Specialized
Module conforming to the ADR-033 6-point standard. It generates tiered variants
(below/at/above grade + ELL) of an approved `ArtifactContent` via `content_creator` on
`AgentRuntime`; IEP is deferred. Each variant is a full `ArtifactContent` that passes
compliance + quality gates, renders, and is exportable, surfaced at the teacher gate as sibling
variants.

## Scope

- [ ] Scaffold via `make new-module KIND=agent NAME=differentiation` (or extend
      `content_creator` per RFC "Runtime design" decision); register capabilities binding read
      + generation only, never `write_file`/`task`
      (`packages/agents/tools/capabilities.py:35-39, 48-58`).
- [ ] Contract (point 1): additive fields `variant_of_artifact_id`, `differentiation_tier`
      (`Literal["below","at","above"]`), `differentiation_support` (`Literal["ell"]`, v1),
      `differentiation_notes` on `ArtifactContent` (`common/contracts/artifact.py:46-110`) —
      non-breaking per MOD-04; preserve Pydantic↔Zod parity. `iep` reserved, not emitted.
- [ ] Generation: one LLM call per (tier × support) via
      `runtime.complete_compiled_json_with_retries`, mirroring
      `packages/agents/sub_agents/content_creator/nodes.py:72-113`;
      `AgentRuntimeConfig(agent="differentiation", …, model="4omc")`; no direct transport.
- [ ] Gates: each variant runs the same compliance
      (`packages/agents/teaching_pack/compliance.py`) + quality (`readability_level`,
      `learning_objective_alignment` middleware); failing variants are dropped, not surfaced.
- [ ] Observability (point 4) per variant; fail-closed (point 5): readability/safety breach ⇒
      variant discarded + `step_failed`; refuse to run on an unapproved source. Run under MOD-05
      fault boundary (per-variant timeout; single-variant failure = dependency-skip).
- [ ] Rendering: variants render through the existing plugin for their `artifact_type`
      (`packages/renderer/src/core/registry.ts`) — no new renderer plugin.
- [ ] Manifest/version entry (point 6) via MOD-03.
- [ ] Tests (point 3): contract, guard, live-path (below/at/above + ELL from one artifact),
      real-LLM, safety (below-tier over-target variant discarded).

## Acceptance

- All acceptance tests in `docs/rfc/differentiation-module.md` pass.
- MOD-01 conformance passes; MOD-03 shows registered + contract + tests + reachable.
- Real-LLM test (9Router `:20228`, model `4omc`) produces below-grade + ELL variants of a real
  approved artifact; each passes compliance + quality and renders standalone HTML.
- Safety test: a below-tier variant reading above target is discarded and recorded.

## References

- RFC: `docs/rfc/differentiation-module.md`
- `common/contracts/artifact.py:46-110`
- `packages/agents/sub_agents/content_creator/nodes.py:72-113`
- `packages/agents/tools/capabilities.py:35-39, 48-58`
- `packages/agents/middleware/quality/{readability_level,learning_objective_alignment}.py`
- MOD-01, MOD-02, MOD-04, MOD-05

## Implementation notes

- Additive contract fields ⇒ no `schema_version` bump; add per-tier golden fixtures (MOD-04).
- Reuse the content_creator generation + retry path wholesale; the new logic is the tiering
  policy + per-variant gate loop + fail-closed drop.
