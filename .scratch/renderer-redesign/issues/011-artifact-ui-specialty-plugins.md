---
title: Migrate specialty Artifact UI plugins
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate remaining Artifact UI render paths to plugins: `investigation-folder.inverse-thinking`, `paper-dossier.root-cause-session`, and `transit-route.video-route`. Managed inline interactivity must be declared by plugin policy.

## Acceptance criteria

- [x] All three plugins declare complete metadata, schemas, capabilities, sanitizer policies, adapters, and templates.
- [x] Inverse-thinking callers use `render()` instead of `renderInverseThinkingHtml`.
- [x] Root-cause session and video route render through the registry with standalone output and manifests.
- [x] Managed inline JS is allowed only for plugins that declare `{ id, sourcePath, sha256 }`; hash mismatch or undeclared inline script fails asset policy.
- [x] Golden baseline coverage plus focused registry smoke cover representative outputs.

## Implementation notes

- Added `packages/renderer/src/plugins/specialty-artifact-ui.ts` with registry plugins for:
  - `investigation-folder.inverse-thinking`
  - `paper-dossier.root-cause-session`
  - `transit-route.video-route`
- Registered all three specialty plugins in `packages/renderer/src/core/runtime.ts`.
- Migrated `renderInverseThinkingHtml()` in `packages/renderer/src/inverse-thinking-renderer.ts` to call the ADR-025 `render()` API while preserving the legacy return shape (`Promise<string>`).
- Added local Zod boundary schemas for inverse-thinking, root-cause session, and video-route inputs.
- Declared root-cause session interactivity as a managed inline script with `{ id, sourcePath, sha256 }` and updated `root-cause-session.html` to emit `data-managed-script-id="artifact-ui-interactivity"`.
- Added `packages/renderer/__tests__/specialty-artifact-ui-plugins.test.ts` for plugin metadata, batch registry rendering, student projection safety, malformed input rejection, and managed-script hash mismatch failure.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/specialty-artifact-ui-plugins.test.ts __tests__/artifact-ui/render-artifact-ui.test.ts __tests__/core-policy.test.ts` — 3 files, 36 tests passed.
- `pnpm --filter @oh-my-class/renderer build` — passed.
- LSP diagnostics clean for `packages/renderer/src/plugins/specialty-artifact-ui.ts`, `packages/renderer/src/core/runtime.ts`, `packages/renderer/src/inverse-thinking-renderer.ts`, and `packages/renderer/__tests__/specialty-artifact-ui-plugins.test.ts`.
- Manual built-package library-surface smoke used `packages/renderer/dist/renderer.js` and `packages/renderer/dist/inverse-thinking-renderer.js` to render inverse-thinking, root-cause session, and video-route outputs; observed standalone HTML, no external assets, managed script tagging, no teacher-only leakage in student projections, and legacy inverse-thinking wrapper output through the registry theme.
- Known warning during tests/manual smoke: `sanitize-html` warns that allowing `<style>` is XSS-sensitive; this is an existing standalone-HTML renderer policy warning, not a failing gate.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 007-lesson-answer-key-plugins.md
- 010-navy-ticket-vocabulary-plugins.md
