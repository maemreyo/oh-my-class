---
title: Renderer core kernel with fixture plugin
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Build the minimal production-shaped renderer kernel with a single fixture plugin that proves the full path: `render({ kind, input, context })` validates input, resolves a plugin, adapts data, renders an Eta template, sanitizes output, enforces standalone asset policy, and returns HTML with manifest, diagnostics, and metrics.

This is the tracer bullet for the rewrite. It should not migrate real artifacts yet.

## Acceptance criteria

- [x] Public `render()` and `renderBatch()` APIs exist with `RenderRequest`, `RenderResponse`, `RenderContext`, and `RenderManifest` types.
- [x] Plugin registry supports registration, duplicate-kind rejection, unknown-kind errors, metadata inspection, and typed `RendererError` outputs.
- [x] A fixture plugin renders standalone HTML end-to-end and returns manifest, diagnostics, and metrics.
- [x] Runtime schema validation is required before adapter execution.
- [x] Unit tests cover success, validation failure, unknown kind, unsupported audience, and fixture manifest creation.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md

## Implementation

- Added the parallel core kernel under `packages/renderer/src/core/`.
- Added `RendererError` with typed codes/categories for registry, validation, policy, and template failures.
- Added `PluginRegistry`, duplicate-kind protection, unknown-kind errors, metadata inspection, `render()`, and `renderBatch()`.
- Added the first fixture plugin at `packages/renderer/src/plugins/fixture.ts` and template `packages/renderer/templates/fixture/echo.html`.
- Re-exported the new kernel API from `packages/renderer/src/renderer.ts` while preserving existing legacy exports for later migration issues.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/core-renderer-kernel.test.ts` passed: 8 tests.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/core-renderer-kernel.test.ts __tests__/current-renderer-baselines.test.ts` passed: 9 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` on `packages/renderer/src/core`, `packages/renderer/src/plugins/fixture.ts`, and `packages/renderer/__tests__/core-renderer-kernel.test.ts` reported no diagnostics.
- Manual library-surface check passed by importing `render()` from `packages/renderer/dist/renderer.js` and rendering `fixture.echo`; observed `fixture.echo` manifest and content hash.
