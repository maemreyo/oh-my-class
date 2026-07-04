# [MOD-08] Build Localization module on AgentRuntime + Module Standard

Status: TODO
Labels: module-standard, agents, renderer, localization
ADR: 033
Depends on: MOD-01, MOD-02

## Context

Build the Localization module per `docs/rfc/localization-agent.md` as a Specialized Module
conforming to the ADR-033 6-point standard. It produces localized artifact variants without a
parallel artifact model, preserves standalone-HTML invariants + answer-key separation, and
keeps locale choices config-driven. It does not exist yet; scaffold via MOD-02 (`KIND=agent`),
plus renderer + theme changes.

## Scope

- [ ] Scaffold `packages/agents/sub_agents/localization/` via `make new-module KIND=agent
      NAME=localization`; `AGENT_CAPABILITIES["localization"]` binds read + localization prompt
      modules only; never `write_file` (RFC "Runtime design").
- [ ] Runtime: `AgentRuntimeConfig(agent="localization", …, model="4omc")`; artifacts flow
      through state, never written directly.
- [ ] Contract (point 1): add i18n metadata (`locale` BCP-47, `source_locale`,
      `localized_from_artifact_id`, `translation_notes`) as **additive** fields to artifact
      contracts (non-breaking per MOD-04); keep `ArtifactContent.accessibility.language`
      (`common/contracts/artifact.py:68`) as the student-facing indicator. Preserve Pydantic↔Zod
      parity.
- [ ] Renderer changes: `dir="rtl"` for RTL locales; locale-aware date/number formatting with
      no external libraries; system-stack fonts only (no CDN); snapshot localized lesson,
      worksheet, quiz outputs (RFC "Renderer changes"). Apply within existing renderer plugins
      (`packages/renderer/src/plugins/*.ts`), not a parallel renderer.
- [ ] Theme changes: optional locale token overrides in `theme.json`
      (`font_stack_locale_overrides`, `line_height_locale_overrides`,
      `text_density_locale_overrides`); generated `theme_*.css` stays derived output (respect
      `verify_registry_drift.py` theme-hash checks at
      `scripts/verify_registry_drift.py:176-234`).
- [ ] Observability (point 4); fail-closed (point 5) under MOD-05; manifest/version (point 6)
      via MOD-03.
- [ ] Tests (point 3): contract (i18n fields + language consistency), renderer (localized
      standalone HTML, no external assets), guard, real-LLM.

## Acceptance

- All acceptance tests in `docs/rfc/localization-agent.md` pass.
- MOD-01 conformance passes for `localization`; MOD-03 shows registered + contract + tests +
  reachable.
- Real-LLM test (9Router `:20228`, model `4omc`) produces Vietnamese and English variants;
  localized standalone HTML has no external assets and preserves answer-key separation.
- Theme-hash drift stays clean after adding locale override tokens (regenerate + verify).

## References

- RFC: `docs/rfc/localization-agent.md`
- `common/contracts/artifact.py:68`
- `packages/renderer/src/plugins/*.ts`, `packages/renderer/src/core/registry.ts`
- `scripts/verify_registry_drift.py:176-234`
- `packages/agents/runtime.py:34-49`
- MOD-01 spec, MOD-02 scaffolder, MOD-04 versioning, MOD-05 fault boundary

## Implementation notes

- i18n fields are additive ⇒ no `schema_version` bump; still add golden fixtures per MOD-04 for
  localized outputs so RTL/formatting regressions are caught.
- Reuse the existing standalone-HTML invariant checks (no CDN — see
  `content_creator/nodes.py:174-183` `validate_no_cdn`) for localized outputs.
