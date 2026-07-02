---
title: Implement teaching_pack as a bundle plugin
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Implement `teaching_pack` as a bundle plugin that renders child artifacts through the registry instead of pretending to be a lesson. The bundle output must preserve child manifests and provide a bundle-level manifest.

## Acceptance criteria

- [x] `teaching_pack` plugin validates bundle input and rejects malformed child artifacts.
- [x] Child artifacts render through `renderBatch()` or an equivalent internal registry call.
- [x] Bundle response includes child manifests and a bundle manifest.
- [x] Partial failure behavior is explicit and tested.
- [x] `teaching_pack` no longer falls through to lesson rendering.

## Implementation notes

- Added `packages/renderer/src/plugins/teaching-pack.ts` and registered it in the default plugin registry.
- Added `packages/renderer/templates/pages/teaching_pack.html` for bundle rendering.
- Extended core render services with `renderChild()` so bundle plugins can render children through the same registry/theme resolver path.
- Extended `RenderManifest` with `childManifests` for bundle-level manifest preservation.
- Added `packages/renderer/__tests__/teaching-pack-plugin.test.ts` covering metadata, child rendering, print mode, malformed child failure, malformed bundle failure, and no lesson fallback.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/teaching-pack-plugin.test.ts __tests__/missing-contract-plugins.test.ts __tests__/lesson-answer-key-plugins.test.ts __tests__/summary-visual-plugins.test.ts __tests__/practice-plugins.test.ts __tests__/quiz-plugin.test.ts __tests__/core-policy.test.ts __tests__/core-renderer-kernel.test.ts` — 8 files, 45 tests passed.
- `pnpm --filter @oh-my-class/renderer build` — passed.
- LSP diagnostics clean for `packages/renderer/src/core/types.ts`, `packages/renderer/src/core/render.ts`, `packages/renderer/src/plugins/teaching-pack.ts`, `packages/renderer/src/core/runtime.ts`, and `packages/renderer/__tests__/teaching-pack-plugin.test.ts`.
- Manual library-surface check rendered a `teaching_pack` bundle with `lesson` and `exit_ticket` children, preserved child manifests, produced standalone inline-only HTML, and rejected a malformed child with `validation_failed`.
- Known warning during tests: `sanitize-html` warns that allowing `<style>` is XSS-sensitive; this is an existing standalone-HTML renderer policy warning, not a failing gate.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 005-practice-plugins.md
- 006-summary-visual-plugins.md
- 007-lesson-answer-key-plugins.md
- 008-missing-contract-plugins.md
