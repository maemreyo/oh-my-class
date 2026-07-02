---
title: Migrate quiz as the first real Artifact-Kind plugin
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `quiz` into a self-contained plugin that uses runtime schema validation, the unified theme resolver, sanitizer chokepoint, standalone asset policy, message catalog, manifest generation, and representative snapshots. This establishes the regular artifact plugin pattern.

## Acceptance criteria

- [x] `quiz` plugin declares kind, version, schema, capabilities, sanitizer policy, adapter, and template path.
- [x] Rendering `kind: "quiz"` produces standalone HTML with manifest, diagnostics, and metrics.
- [x] Student output passes leak-prevention checks for answer and explanation fields where applicable.
- [x] Golden snapshots cover preview/export/print where supported.
- [x] Existing quiz renderer callers are either migrated or explicitly blocked until the public API migration issue.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 001-core-renderer-kernel.md
- 003-theme-sanitizer-asset-policy.md

## Implementation

- Added `packages/renderer/src/plugins/quiz.ts` as the first real regular artifact plugin.
- Registered `quiz` in the default plugin registry next to the fixture plugin.
- Added runtime Zod validation, student/teacher audience behavior, quiz sanitizer policy selection, and `pages/quiz` template routing.
- Left existing legacy `renderArtifact("quiz", ...)` and agent-renderer callers in place; caller cutover remains blocked until Issue 014.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/quiz-plugin.test.ts __tests__/core-renderer-kernel.test.ts __tests__/current-renderer-baselines.test.ts` passed: 14 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` on `packages/renderer/src/plugins/quiz.ts`, `packages/renderer/src/core/runtime.ts`, and `packages/renderer/__tests__/quiz-plugin.test.ts` reported no diagnostics.
- Manual library-surface check passed by rendering `kind: "quiz"` from `packages/renderer/dist/renderer.js`; observed `manifest.kind = "quiz"` and confirmed student output did not include the explanation.

Note: focused renderer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags.
