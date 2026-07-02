---
title: Scalability validation — add-a-family checklist and docs
status: ready-for-agent
labels: [renderer, documentation, scalability]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Validate the scalability design by documenting the exact steps to add a new artifact UI family. This is a documentation + validation issue, not implementation. The goal is to prove that adding a 5th family (e.g., "science-lab") requires only:

1. CSS files (token + family)
2. Eta templates
3. Contract adapter
4. Registry entry

And NO changes to: loader, renderer, existing families, existing tests.

## Acceptance criteria

- [ ] `docs/artifact-ui-adding-a-family.md` exists with step-by-step checklist
- [ ] Checklist includes: folder structure, CSS file requirements, template requirements, adapter requirements, registry entry format
- [ ] Checklist includes: testing requirements (CSS contract tests, standalone HTML tests, visual QA)
- [ ] Checklist includes: common pitfalls (namespace collisions, missing contract fields, student projection leakage)
- [ ] Checklist explicitly states: **no sanitizer config is needed for a new family** — `sanitizeArtifactUi()` uses a single shared `ARTIFACT_UI_CONFIG` (Issue 014). Adding a family is exactly 4 artifacts: CSS (tokens + family), Eta templates, adapter, registry entry.
- [ ] Checklist explicitly states: **`ArtifactDataMap` is NOT modified** when adding a new family — family types are render-layer concepts, not schema-layer types (see Issue 014 design note).
- [ ] Example: document how "science-lab" family would be added (hypothetical, not implemented)
- [ ] ADR-024 §8 (Scalability) is referenced in the docs
- [ ] Docs include the family registry interface (`ArtifactFamily`) with field descriptions
- [ ] Docs include the CSS loading order (contract → family tokens → primitives → family components)
- [ ] Docs note that `loadArtifactCSS()` is memoized (Issue 016) — no performance concern for batch renders

## Detailed test suite

- [ ] `docs/artifact-ui-adding-a-family.md` exists and is readable
- [ ] Checklist has ≥ 10 actionable steps
- [ ] Example includes all 4 required artifacts (CSS, templates, adapter, registry entry)
- [ ] No step requires modifying files outside `src/artifact-ui/` or `templates/artifact/`

## Verification

- Manual: follow the checklist step-by-step for a hypothetical "science-lab" family
- Manual: verify no step requires touching `loader.ts`, `index.ts`, or existing family files
- Manual: verify checklist covers all 4 required artifacts

## Blocked by

- `001` through `009` — all implementation must be complete to validate the pattern works
