# [MOD-07] Build Accessibility module on AgentRuntime + Module Standard

Status: TODO
Labels: module-standard, agents, quality, accessibility
ADR: 033
Depends on: MOD-01, MOD-02

## Context

Build the Accessibility module per `docs/rfc/accessibility-agent.md` as a Specialized Module
conforming to the ADR-033 6-point standard. It enriches generated artifacts with alt text,
reading-level controls, and WCAG checks, writing all output under
`ArtifactContent.accessibility` (`common/contracts/artifact.py:68`) — no parallel field. It
does not exist yet as a sub-agent; scaffold it via MOD-02 (`KIND=agent`).

## Scope

- [ ] Scaffold `packages/agents/sub_agents/accessibility/` via `make new-module KIND=agent
      NAME=accessibility`; add `AGENT_CAPABILITIES["accessibility"]` binding read capabilities
      only (no `write_file`, no `task`), mirroring
      `packages/agents/tools/capabilities.py:40-45, 48-58`.
- [ ] Runtime: `AgentRuntimeConfig(agent="accessibility", …, model="4omc")`; consume artifact
      JSON + quality findings, return patched `ArtifactContent` via state; never write rendered
      HTML (RFC "Runtime design").
- [ ] Contract (point 1): outputs validate through `ArtifactContent.accessibility` only
      (`language`, `reading_level`, `alt_texts`, `wcag_level`, `wcag_findings`, `adaptations`);
      preserve Pydantic↔Zod parity.
- [ ] Deterministic WCAG checks before any LLM enrichment (alt text present, hierarchical
      headings, accessible names, contrast tokens where available, no hidden teacher answers)
      — LLM supplements, never replaces (RFC "WCAG checks").
- [ ] Observability (point 4): `step_started`/`step_completed`/`step_failed`.
- [ ] Fail-closed (point 5): missing alt text yields a finding + generated replacement; a
      WCAG hard failure blocks rather than silently passes. Run under MOD-05 fault boundary.
- [ ] Manifest/version entry (point 6) via MOD-03.
- [ ] Tests (point 3): contract, quality (missing alt text → finding + replacement), renderer
      smoke (enriched artifact still renders standalone HTML), guard, real-LLM.

## Acceptance

- All acceptance tests in `docs/rfc/accessibility-agent.md` pass.
- MOD-01 conformance passes for `accessibility`; MOD-03 shows registered + contract + tests +
  reachable.
- Real-LLM test (9Router `:20228`, model `4omc`) covers one image-heavy and one text-heavy
  artifact; enriched output still renders standalone HTML with no external assets.
- Guard test: uses `AgentRuntime` and declared capabilities only.

## References

- RFC: `docs/rfc/accessibility-agent.md`
- `common/contracts/artifact.py:68`
- `packages/agents/tools/capabilities.py:40-45, 48-58`
- `packages/agents/runtime.py:34-49`
- MOD-01 spec, MOD-02 scaffolder, MOD-05 fault boundary

## Implementation notes

- Deterministic checks are the safety floor; keep them independent of the LLM so the module is
  useful (and fail-closed) even when the model is unavailable.
- Reuse existing quality-layer findings shapes rather than a new report format.
