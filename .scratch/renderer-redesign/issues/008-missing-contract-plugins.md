---
title: Add first-class plugins for previously missing contract types
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Add first-class plugins for `flashcard_deck`, `reading_passage`, `exit_ticket`, and `roadmap` so these existing contract types no longer fall through to lesson rendering or remain sanitizer-only concepts.

## Acceptance criteria

- [x] All four plugins declare complete plugin metadata, schemas, capabilities, sanitizer policies, adapters, and templates.
- [x] Each plugin renders through `render()` with standalone output and a manifest.
- [x] Registry completeness tests include all four kinds.
- [x] Golden snapshots cover representative input for each plugin.
- [x] Print support is declared and tested for printable kinds.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md

## Implementation

- Added `packages/renderer/src/plugins/flashcard-deck.ts` with complete plugin metadata, Zod boundary schema, print capability, sanitizer policy, and `pages/flashcard_deck` template routing.
- Added `packages/renderer/src/plugins/reading-passage.ts` with complete plugin metadata, Zod boundary schema, print capability, student-safe answer omission, and `pages/reading_passage` template routing.
- Added `packages/renderer/src/plugins/exit-ticket.ts` with complete plugin metadata, Zod boundary schema, print capability, and `pages/exit_ticket` template routing.
- Added `packages/renderer/src/plugins/roadmap.ts` with complete plugin metadata, Zod boundary schema, print capability, and `pages/roadmap` template routing.
- Registered all four plugins in `packages/renderer/src/core/runtime.ts` so `render()` handles `flashcard_deck`, `reading_passage`, `exit_ticket`, and `roadmap` through the new registry.
- Extended `packages/renderer/src/core/sanitizer.ts` and `packages/renderer/src/core/types.ts` with policy entries for the missing-contract artifact kinds.
- Added `packages/renderer/__tests__/missing-contract-plugins.test.ts` covering registry completeness, standalone manifests, snapshots, print mode, validation failures, and reading-passage answer leak prevention.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/missing-contract-plugins.test.ts -u` passed and wrote/updated representative snapshots.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/missing-contract-plugins.test.ts __tests__/lesson-answer-key-plugins.test.ts __tests__/summary-visual-plugins.test.ts __tests__/practice-plugins.test.ts __tests__/quiz-plugin.test.ts __tests__/core-policy.test.ts __tests__/core-renderer-kernel.test.ts` passed: 40 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` reported no diagnostics for the four new plugin files, `packages/renderer/src/core/types.ts`, `packages/renderer/src/core/sanitizer.ts`, `packages/renderer/src/core/runtime.ts`, and `packages/renderer/__tests__/missing-contract-plugins.test.ts`.
- Manual library-surface check rendered all four kinds from `packages/renderer/dist/renderer.js` in print mode; each returned the expected manifest kind, standalone HTML, print CSS, no external `http(s)://` asset reference, and reading passage did not leak the hidden answer sentinel.
- Post-write size check: `core/types.ts` 97 pure LOC, `core/sanitizer.ts` 55, `flashcard-deck.ts` 38, `reading-passage.ts` 59, `exit-ticket.ts` 39, `roadmap.ts` 52, `runtime.ts` 30, `missing-contract-plugins.test.ts` 132.

Note: focused renderer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags.
