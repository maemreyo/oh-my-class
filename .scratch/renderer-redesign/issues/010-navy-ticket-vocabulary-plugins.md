---
title: Migrate navy-ticket semantic-anchor vocabulary plugins
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate semantic-anchor vocabulary rendering to `navy-ticket.teaching` and `navy-ticket.practice` plugins. Vocabulary batch export should call `render()` or `renderBatch()` rather than semantic-anchor wrapper functions.

## Acceptance criteria

- [x] `navy-ticket.teaching` and `navy-ticket.practice` plugins validate semantic-anchor inputs and declare audience policies.
- [x] Teacher and student projections render through the new registry API.
- [x] Vocabulary batch exporter uses `renderBatch()` and receives manifests for all four projections.
- [x] Public semantic-anchor wrapper exports are no longer required by production callers.
- [x] Golden baseline coverage plus focused registry behavior tests cover teaching/practice and teacher/student variants.

## Implementation notes

- Added `packages/renderer/src/plugins/navy-ticket.ts` and registered `navyTicketTeachingPlugin` and `navyTicketPracticePlugin` in the default registry.
- Added local Zod boundary schemas for semantic-anchor cluster and practice-set inputs, with fail-closed `validation_failed` behavior for malformed inputs.
- Reused the existing navy-ticket Artifact UI adapters and templates while routing through the ADR-025 `render()` / `renderBatch()` kernel.
- Added `artifact_ui` sanitizer-policy support so registry-rendered navy-ticket projections use the existing Artifact UI sanitizer configuration.
- Updated `packages/exporters/src/vocabulary-batch/index.ts` so HTML batch export calls `renderBatch()` and stores renderer manifests on every generated projection file entry.
- Fixed built-package Artifact UI asset resolution so `packages/renderer/dist/renderer.js` can load source CSS/JS assets used by the templates.
- Added `packages/renderer/__tests__/navy-ticket-plugins.test.ts` for plugin metadata, teacher/student projection behavior, no student leakage, batch manifests, and malformed input failures.
- Extended `packages/exporters/__tests__/vocabulary-batch.test.ts` to assert embedded renderer manifests for vocabulary-batch HTML exports.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/navy-ticket-plugins.test.ts __tests__/semantic-anchor-projections.test.ts __tests__/current-renderer-baselines.test.ts` — 3 files, 8 tests passed.
- `pnpm --filter @oh-my-class/exporters exec vitest run __tests__/vocabulary-batch.test.ts` — 1 file, 4 tests passed.
- `pnpm --filter @oh-my-class/renderer build` — passed.
- `pnpm --filter @oh-my-class/exporters build` — passed.
- LSP diagnostics clean for `packages/renderer/src/plugins/navy-ticket.ts`, `packages/renderer/src/artifact-ui/loader.ts`, `packages/renderer/src/artifact-ui/renderer.ts`, `packages/renderer/__tests__/navy-ticket-plugins.test.ts`, `packages/exporters/src/vocabulary-batch/index.ts`, and `packages/exporters/__tests__/vocabulary-batch.test.ts`.
- Manual built-package library-surface smoke used `packages/renderer/dist/renderer.js` and `packages/exporters/dist/vocabulary-batch/index.js` to render all four navy-ticket projections, confirm standalone inline-only HTML, confirm no teacher-only marker leakage in student projections, and produce a vocabulary-batch ZIP with renderer manifests for all four HTML projections.
- Known warning during tests/manual smoke: `sanitize-html` warns that allowing `<style>` is XSS-sensitive; this is an existing standalone-HTML renderer policy warning, not a failing gate.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
