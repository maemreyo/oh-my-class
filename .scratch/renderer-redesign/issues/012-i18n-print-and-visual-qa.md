---
title: Add renderer i18n catalog, print mode, and visual QA smoke
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Add centralized renderer UI messages for Vietnamese and English, make print mode first-class, and add visual/print smoke tests for representative regular and Artifact UI plugins.

## Acceptance criteria

- [x] `MessageCatalog` resolves renderer chrome labels by locale and fails tests for missing keys.
- [x] `renderMode: "print"` is supported by printable plugins or rejected with a typed unsupported-mode error.
- [x] Visual smoke covers representative regular and Artifact UI plugins.
- [x] Print smoke covers quiz and lesson output.
- [ ] Templates use message keys for renderer chrome instead of hard-coded labels. (deferred — messages are merged into templateData and available as `it.messages[key]`; template migration is a future polish task)

## Implementation notes

- Created `packages/renderer/src/i18n/catalog.ts` with `MessageKey`, `Messages`, `VI_MESSAGES`, `EN_MESSAGES`, `resolveMessages()`, and `assertAllKeysPresent()`.
- `render()` in `core/render.ts` merges `resolveMessages(locale)` into templateData after `adapt()`: `templateData = { ...adaptedData, messages }`. All plugins gain access to locale-aware labels.
- `RendererErrorCode.UnsupportedMode` added to `core/errors.ts`. Print mode validation added to `render()`: throws `UnsupportedMode` when `renderMode === "print"` and `!plugin.capabilities.supportsPrint`.
- Added `__tests__/i18n-print-visual-smoke.test.ts` (10 tests): catalog completeness for both locales, print mode rejection/acceptance, visual/print smoke, and manifest field verification.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/i18n-print-visual-smoke.test.ts` — 10 tests passed.
- `pnpm --filter @oh-my-class/renderer build` — clean TypeScript build.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 005-practice-plugins.md
- 007-lesson-answer-key-plugins.md
- 011-artifact-ui-specialty-plugins.md
