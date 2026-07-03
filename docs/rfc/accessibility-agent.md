# RFC: Accessibility agent for alt text, reading level, and WCAG

Status: Proposed  
Owner: agents + quality  
Depends on: ADR-018 runtime parity, Issue #26 `AgentRuntime`, existing `ArtifactContent.accessibility`

## Context

The Accessibility agent enriches generated artifacts with alt text, reading-level controls, and WCAG checks. The contract surface already exists through `ArtifactContent.accessibility`; this RFC keeps that as the single output field.

## Output mapping

Write all outputs under `ArtifactContent.accessibility`:

- `language`
- `reading_level`
- `alt_texts`
- `wcag_level`
- `wcag_findings`
- `adaptations`

No parallel accessibility field is introduced.

## Runtime design

The agent uses `AgentRuntimeConfig(agent="accessibility", run_id, step, step_label, model="4omc")`. It consumes artifact JSON and quality findings, then returns patched artifact content. The teaching-pack graph owns orchestration; the agent never writes rendered HTML.

## WCAG checks

Minimum deterministic checks before any LLM enrichment:

- every non-decorative image/component has alt text;
- headings are hierarchical;
- links/buttons have accessible names;
- color contrast tokens meet WCAG AA where token data is available;
- student-facing content has no hidden teacher-only answers.

LLM checks supplement, not replace, deterministic checks.

## Reading-level targets

The target comes from `class_info.grade` and subject. The agent reports:

- target grade band;
- estimated reading level;
- simplification notes when content is above target.

## Acceptance tests

- Contract test: accessibility output validates through `ArtifactContent.accessibility` only.
- Quality test: missing alt text yields a finding and a generated replacement.
- Renderer smoke: enriched artifact still renders standalone HTML.
- Guard test: agent uses `AgentRuntime` and declared capabilities only.
- Real-LLM test through 9Router `:20228`, model `4omc`, for one image-heavy artifact and one text-heavy artifact.
