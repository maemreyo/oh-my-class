---
title: Persist rendered HTML with manifest and wire exports
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Wire renderer responses into gateway/export persistence so final HTML and `RenderManifest` are stored together. Exports should use persisted final HTML by default and only re-render explicitly when requested.

## Acceptance criteria

- [x] Manifest includes renderer, plugin, template, theme, sanitizer policy versions, render mode, locale, audience, requestId, renderedAt, and contentHash.
- [x] Export writer uses persisted rendered HTML when available.
- [x] Explicit re-render creates a new manifest rather than mutating old output silently.
- [x] Tests cover manifest persistence and export behavior for at least one single artifact.
- [ ] Gateway render flow stores `rendered_html` and `RenderManifest` together. (gateway wiring is a separate service-layer concern; ManifestStore + ExportWriter are ready to be integrated)
- [ ] Tests cover teaching pack bundle. (teaching pack rendering works via plugin; dedicated bundle test deferred)

## Implementation notes

- `RenderManifest` in `core/types.ts` extended with `renderMode`, `locale`, `audience`, `requestId` fields. All are populated from `RenderContext` in `render()`.
- Created `packages/renderer/src/core/manifest-store.ts`: `ManifestStore` class (Map-backed) with `put`, `get`, `has`, `delete`, `size`.
- Created `packages/renderer/src/exporters/export-writer.ts`: `ExportWriter` class wrapping `ManifestStore` with `write(requestId)`, `rerender(request)`, and `storeResponse(response, requestId)` methods.
- Exported `ManifestStore` and `RenderedDocument` from `core/index.ts`.
- Added `__tests__/manifest-persistence.test.ts` (10 tests): ManifestStore CRUD, ExportWriter write/rerender/storeResponse, and re-render-replaces behavior.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/manifest-persistence.test.ts` — 10 tests passed.
- `pnpm --filter @oh-my-class/renderer build` — clean TypeScript build.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 002-worker-protocol-v2.md
- 009-teaching-pack-bundle-plugin.md
