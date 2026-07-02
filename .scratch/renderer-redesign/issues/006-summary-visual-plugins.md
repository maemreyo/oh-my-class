---
title: Migrate recap and infographic plugins end-to-end
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `recap` and `infographic` into registry plugins to prove non-question artifacts and visual-heavy artifacts under the new renderer kernel.

## Acceptance criteria

- [x] `recap` and `infographic` plugins declare complete plugin metadata and runtime schemas.
- [x] Both plugins render through `render()` with standalone output and manifests.
- [x] Infographic output preserves safe inline visual content while passing asset policy.
- [x] Golden snapshots cover representative recap and infographic inputs.
- [x] Visual smoke coverage exists for infographic output.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md

## Implementation

- Added `packages/renderer/src/plugins/recap.ts` with complete plugin metadata, Zod boundary schema, base sanitizer policy, and `pages/recap` template routing.
- Added `packages/renderer/src/plugins/infographic.ts` with complete plugin metadata, Zod boundary schema, infographic sanitizer policy, and `pages/infographic` template routing.
- Extended `packages/renderer/src/core/sanitizer.ts` and `packages/renderer/src/core/types.ts` so the new kernel can select the existing infographic sanitizer config.
- Registered both plugins in `packages/renderer/src/core/runtime.ts` so `render({ kind: "recap" | "infographic" })` works through the default registry.
- Added `packages/renderer/__tests__/summary-visual-plugins.test.ts` covering metadata, standalone manifests, print mode, validation failures, representative snapshots, and safe inline SVG preservation.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/summary-visual-plugins.test.ts -u` passed and wrote 2 snapshots.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/summary-visual-plugins.test.ts __tests__/practice-plugins.test.ts __tests__/quiz-plugin.test.ts __tests__/core-policy.test.ts __tests__/core-renderer-kernel.test.ts` passed: 28 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` reported no diagnostics for `packages/renderer/src/core/types.ts`, `packages/renderer/src/core/sanitizer.ts`, `packages/renderer/src/plugins/recap.ts`, `packages/renderer/src/plugins/infographic.ts`, `packages/renderer/src/core/runtime.ts`, and `packages/renderer/__tests__/summary-visual-plugins.test.ts`.
- Manual library-surface check rendered `recap` and `infographic` from `packages/renderer/dist/renderer.js` in print mode; both returned matching manifests, contained print CSS, infographic preserved inline `<svg>/<rect>`, and no external `http(s)://` asset reference appeared.
- Post-write size check: `core/types.ts` 97 pure LOC, `core/sanitizer.ts` 37, `recap.ts` 38, `infographic.ts` 43, `runtime.ts` 11, `summary-visual-plugins.test.ts` 89.

Note: focused renderer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags.
