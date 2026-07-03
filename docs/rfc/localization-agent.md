# RFC: Localization agent for multilingual artifacts

Status: Proposed  
Owner: agents + renderer  
Depends on: ADR-018 runtime parity, Issue #26 `AgentRuntime`

## Context

The Localization agent produces multilingual teaching artifacts after the foundation is in place. It is cross-cutting: agent runtime, contracts, renderer, and brand tokens all need explicit seams before implementation.

## Goals

- Generate localized artifact variants without creating a parallel artifact model.
- Preserve standalone HTML invariants and answer-key separation.
- Keep locale-aware choices config-driven through contracts and `theme.json`.

## Contract changes

Add i18n metadata to artifact contracts:

- `locale`: BCP-47 language tag for the artifact variant.
- `source_locale`: original language when translated.
- `localized_from_artifact_id`: optional source artifact reference.
- `translation_notes`: teacher-visible notes for culturally adapted examples.

Existing `ArtifactContent.accessibility.language` remains the student-facing language indicator; the new i18n fields describe localization provenance.

## Renderer changes

- Render `dir="rtl"` for right-to-left locales.
- Choose locale-aware date/number formatting without external libraries in standalone HTML.
- Keep fonts on the system stack; no locale-specific CDN font loading.
- Snapshot localized lesson, worksheet, and quiz outputs.

## Theme changes

Extend each `theme.json` with optional locale token overrides:

- `font_stack_locale_overrides`
- `line_height_locale_overrides`
- `text_density_locale_overrides`

Generated `theme_*.css` remains derived output and must not be edited manually.

## Runtime design

The agent uses `AgentRuntimeConfig(agent="localization", run_id, step, step_label, model="4omc")`. It binds only read capabilities and localization-specific prompt modules. It must not write files directly; artifacts flow through state.

## Acceptance tests

- Contract test for i18n fields and `ArtifactContent.accessibility.language` consistency.
- Renderer test for localized standalone HTML with no external assets.
- Guard test that the agent uses `AgentRuntime` and declared capabilities only.
- Real-LLM test through 9Router `:20228`, model `4omc`, for Vietnamese and English variants.
