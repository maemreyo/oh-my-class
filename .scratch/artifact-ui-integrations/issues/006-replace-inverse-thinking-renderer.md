---
title: Replace inverse-thinking-renderer.ts with Artifact UI
status: ready-for-agent
labels: [renderer, migration, inverse-thinking]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Replace the inline `inverse-thinking-renderer.ts` renderer with Artifact UI rendering via `renderArtifactUi()`. The old renderer generates HTML with inline CSS and manual string building. The new renderer uses Artifact UI CSS classes, Eta templates, and the investigation-folder family.

This is a clean replacement — the old file is deleted after parity is verified.

## Current state

`packages/renderer/src/inverse-thinking-renderer.ts`:
- Exports `renderInverseThinkingHtml()`
- Uses inline CSS via `styles()` function (~200 lines of hardcoded CSS)
- Manually builds HTML strings with detective_case/neutral frame support
- Handles teacher/student projection via `isTeacherOnly` boolean
- Called by agent workers for inverse-thinking artifacts

## Target state

- `renderInverseThinkingHtml()` calls `renderArtifactUi()` with investigation-folder family
- Old inline CSS (`styles()` function) is deleted
- Old manual HTML generation is deleted
- Public API signature remains identical (backward-compatible)
- Detective/neutral frame support is implemented via template conditional (see `017-investigation-folder-frame-variants.md`): single template, adapter sets `frameVariant: 'detective' | 'neutral'`, CSS modifier classes `art-folder-cover--detective` / `art-folder-cover--neutral`

## Acceptance criteria

- [ ] `renderInverseThinkingHtml()` produces HTML with `data-artifact-theme="investigation-folder"` on root element
- [ ] `renderInverseThinkingHtml()` output uses `art-*` CSS classes (not inline styles)
- [ ] Teacher projection contains `art-projection-flag` and `art-teacher-block` markers
- [ ] Student projection contains zero `art-teacher-block` or `art-projection-flag` elements
- [ ] Student projection excludes `teacher_only.rationale` and `teacher_only.answer_key`
- [ ] Detective/neutral frame support is preserved: detective input → `art-folder-cover--detective`, neutral input → `art-folder-cover--neutral` (per Issue 017)
- [ ] All output is standalone HTML (no external assets, brand string present)
- [ ] Existing callers continue to work without changes
- [ ] Old `styles()` function and inline CSS are removed
- [ ] Public API type (`InverseThinkingRenderInput`) remains unchanged

## Detailed test suite

- [ ] `packages/renderer/__tests__/inverse-thinking-renderer.test.ts` (existing): all existing tests still pass
- [ ] `packages/renderer/__tests__/artifact-ui/migration-inverse-thinking.test.ts`: detective frame output contains `investigation-folder` theme
- [ ] `packages/renderer/__tests__/artifact-ui/migration-inverse-thinking.test.ts`: student output contains zero `art-teacher-block`
- [ ] `packages/renderer/__tests__/artifact-ui/migration-inverse-thinking.test.ts`: output contains `oh-my-class` brand string
- [ ] `packages/renderer/__tests__/artifact-ui/migration-inverse-thinking.test.ts`: output contains no `http://` in href/src

## Verification

- `pnpm --filter @oh-my-class/renderer test` → all tests pass (old + new)
- `pnpm --filter @oh-my-class/renderer build` → builds successfully
- Manual: render a real InverseThinkingRenderInput through the new path, open in browser, compare with old output
- Manual: `grep -c "style=" packages/renderer/src/inverse-thinking-renderer.ts` → 0 (no inline styles)

## Blocked by

- `002-family-registry-and-css-loader.md` — loader must exist
- `003-eta-templates-all-families.md` — investigation-folder templates must exist
- `004-contract-adapters-all-families.md` — investigation-folder adapter must exist
- `007-public-api-render-artifact-ui.md` — renderArtifactUi() must exist
- `017-investigation-folder-frame-variants.md` — frame variant spec must be read before implementing
