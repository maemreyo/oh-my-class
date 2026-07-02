---
title: Replace semantic-anchor-projections.ts with Artifact UI
status: ready-for-agent
labels: [renderer, migration, vocabulary]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Replace the inline `semantic-anchor-projections.ts` renderer with Artifact UI rendering via `renderArtifactUi()`. The old renderer generates HTML with inline CSS and manual string building. The new renderer uses Artifact UI CSS classes, Eta templates, and the navy-ticket family.

This is a clean replacement — the old file is deleted after parity is verified.

## Current state

`packages/renderer/src/semantic-anchor-projections.ts`:
- Exports `renderSemanticAnchorProjection()` and `renderSemanticAnchorProjectionSet()`
- Uses inline CSS (hardcoded `:root` variables, `.anchor-card`, `.practice-item`, etc.)
- Manually builds HTML strings
- Handles teacher/student projection via `isTeacher` boolean
- Called by `agent-renderer.ts` for vocabulary batch artifacts

## Target state

- `renderSemanticAnchorProjection()` calls `renderArtifactUi()` with navy-ticket family
- `renderSemanticAnchorProjectionSet()` calls `renderArtifactUi()` 4 times (teaching teacher/student, practice teacher/student)
- Old inline CSS is deleted
- Old manual HTML generation is deleted
- Public API signature remains identical (backward-compatible)

## Acceptance criteria

- [ ] `renderSemanticAnchorProjection()` produces HTML with `data-artifact-theme="navy-ticket"` on root element
- [ ] `renderSemanticAnchorProjection()` output uses `art-*` CSS classes (not inline styles)
- [ ] `renderSemanticAnchorProjectionSet()` produces 4 separate HTML strings (teaching teacher/student, practice teacher/student)
- [ ] Teacher projection contains `art-projection-flag` and `art-teacher-block` markers
- [ ] Student projection contains zero `art-teacher-block` or `art-projection-flag` elements
- [ ] Student projection excludes: teacher_script_vi, source_notes, edge_cases, answer_key, rationale
- [ ] All output is standalone HTML (no external assets, brand string present)
- [ ] Existing callers (`agent-renderer.ts`) continue to work without changes
- [ ] Old inline CSS is removed from the file (or file is deleted and replaced)
- [ ] Public API types (`SemanticAnchorProjectionRequest`, `SemanticAnchorProjectionSet`) remain unchanged

## Detailed test suite

- [ ] `packages/renderer/__tests__/semantic-anchor-projections.test.ts` (existing): all existing tests still pass
- [ ] `packages/renderer/__tests__/artifact-ui/migration-vocabulary.test.ts`: teacher output contains `art-ticket` class
- [ ] `packages/renderer/__tests__/artifact-ui/migration-vocabulary.test.ts`: student output contains zero `art-teacher-block`
- [ ] `packages/renderer/__tests__/artifact-ui/migration-vocabulary.test.ts`: output contains `oh-my-class` brand string
- [ ] `packages/renderer/__tests__/artifact-ui/migration-vocabulary.test.ts`: output contains no `http://` in href/src
- [ ] `packages/renderer/__tests__/artifact-ui/migration-vocabulary.test.ts`: output starts with `<!DOCTYPE html>`

## Verification

- `pnpm --filter @oh-my-class/renderer test` → all tests pass (old + new)
- `pnpm --filter @oh-my-class/renderer build` → builds successfully
- Manual: render a real SemanticAnchorCluster through the new path, open in browser, compare with old output
- Manual: `grep -c "style=" packages/renderer/src/semantic-anchor-projections.ts` → 0 (no inline styles)

## Blocked by

- `002-family-registry-and-css-loader.md` — loader must exist
- `003-eta-templates-all-families.md` — navy-ticket templates must exist
- `004-contract-adapters-all-families.md` — navy-ticket adapter must exist
- `007-public-api-render-artifact-ui.md` — renderArtifactUi() must exist
