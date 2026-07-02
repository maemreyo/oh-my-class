---
title: Enforce renderer public API boundary and migrate callers
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Make `@oh-my-class/renderer` expose only the new public API and migrate all current production callers to `render()`/`renderBatch()`. Remove public dependency on legacy wrappers.

The actual runtime caller surface is intentionally small: TypeScript render HTML callers are primarily vocabulary batch export, while gateway rendering crosses the subprocess protocol. Treat this as a cutover issue, not a broad application rewrite.

## Acceptance criteria

- [x] `package.json` exports block deep imports into renderer internals.
- [x] Vocabulary batch exporter uses `renderBatch` from new API.
- [x] Inverse-thinking callers use `render()` via `renderInverseThinkingHtml` wrapper (migrated in issue 011).
- [x] `renderAgentArtifact` migrated from `renderArtifact`/`renderArtifactUi` to `render()` for all artifact types.
- [x] Legacy public functions (`renderArtifactSync`, `renderSemanticAnchorProjection`, `renderArtifactUi`) removed from public exports.
- [x] TypeScript build passes without legacy exports.
- [ ] TypeScript builds fail for deep imports outside the public surface. (deep `import type` usage in `packages/exporters` is type-only and erasure-safe; enforcement via exports map is a future tightening step)

## Implementation notes

- `packages/renderer/package.json` exports already restricted to `"."` only — deep runtime imports are blocked.
- `packages/exporters/src/vocabulary-batch/index.ts` already uses `renderBatch` from `@oh-my-class/renderer` (new API).
- `renderAgentArtifact` in `agent-renderer.ts` fully migrated: all artifact types (quiz, worksheet, drill, recap, infographic, lesson, answer_key) now call `render()` with a constructed `RenderContext` (audience always "student" except answer_key which uses "teacher").
- `isContentComponent` and `UnknownContentComponentError` re-exported from `agent-renderer.ts` for downstream consumers.
- Removed from `renderer.ts` public exports: `renderArtifactSync`, `renderSemanticAnchorProjection`, `renderSemanticAnchorProjectionSet`, `renderArtifactUi`, `renderArtifactUiSet`, and their associated type exports. These remain accessible from their source files for internal/baseline testing.

## Verification

- No production code outside `packages/renderer` references removed functions (verified via grep).
- `pnpm --filter @oh-my-class/renderer exec vitest run` — 413 tests passed (50 files).
- `pnpm --filter @oh-my-class/renderer build` — clean TypeScript build.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 002-worker-protocol-v2.md
- 010-navy-ticket-vocabulary-plugins.md
- 011-artifact-ui-specialty-plugins.md
- 013-manifest-persistence-and-export-wiring.md
