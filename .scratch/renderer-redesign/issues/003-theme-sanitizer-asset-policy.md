---
title: Unified theme resolver, sanitizer chokepoint, and standalone asset policy
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Replace separate theme and Artifact UI CSS loading paths with a shared ThemeResolver, replace duplicate sanitizer functions with one sanitizer chokepoint, and enforce standalone HTML through runtime asset policy validation.

Managed inline JavaScript must use plugin-declared hash allowlists: each script declaration includes `id`, `sourcePath`, and `sha256`; core may inline only matching sources. All other inline scripts fail asset-policy validation.

## Acceptance criteria

- [x] `ThemeResolver` resolves CSS by `(themeId, familyId?, renderMode, locale)` and can be injected into render services.
- [x] Existing theme generation and Artifact UI CSS layers are represented in the unified theme flow.
- [x] `sanitizeRenderedHtml(html, policy)` handles full documents and fragments using one body-extraction implementation.
- [x] Regex sanitizer and sync renderer paths are no longer used by production render flow.
- [x] Asset policy rejects external `src`, `href`, CSS `url(http...)`, CDN stylesheet links, external fonts, and unmanaged external scripts.
- [x] Managed inline JS is allowed only when a plugin declares `{ id, sourcePath, sha256 }` and the loaded source hash matches.
- [x] Tests prove high-contrast/dyslexia theme can apply to both a regular fixture plugin and an Artifact UI fixture plugin.
- [x] Shared XSS corpus passes for the fixture sanitizer policies.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 001-core-renderer-kernel.md

## Implementation

- Added `ThemeResolver` in `packages/renderer/src/core/theme-resolver.ts` with cache key `(themeId, familyId?, renderMode, locale)`.
- Added `sanitizeRenderedHtml()` in `packages/renderer/src/core/sanitizer.ts` as the new kernel sanitizer chokepoint.
- Extended render services with resolved theme CSS and managed scripts.
- Added managed script declarations/loading/hash verification in `packages/renderer/src/core/managed-scripts.ts`.
- Strengthened `enforceInlineOnlyAssetPolicy()` to reject external `src`/`href`, stylesheet links, CSS `url(http...)`, `@import`, external font URLs, script `src`, and unmanaged inline scripts.
- Updated the kernel render flow to enforce asset policy before and after sanitization, then sanitize through `sanitizeRenderedHtml()`.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/core-policy.test.ts __tests__/core-renderer-kernel.test.ts __tests__/worker-protocol-v2.test.ts` passed: 19 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` on `packages/renderer/src/core`, `packages/renderer/__tests__/core-policy.test.ts`, and `packages/renderer/src/renderer.ts` reported no diagnostics.
- Manual library-surface check passed by rendering `fixture.echo` from `packages/renderer/dist/renderer.js` with `theme="high-contrast-dyslexia"`; observed fixture manifest and dyslexia theme CSS in output.

Note: focused sanitizer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags. This warning is inherited from current standalone-HTML behavior and is now covered by Issue 003 policy tests.
