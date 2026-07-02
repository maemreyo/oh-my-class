---
title: Migrate worksheet and drill plugins end-to-end
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `worksheet` and `drill` into plugins that follow the quiz tracer pattern and prove printable practice artifacts through the new registry API.

## Acceptance criteria

- [x] `worksheet` and `drill` plugins declare complete plugin metadata and runtime schemas.
- [x] Both plugins render through `render()` with standalone output and manifests.
- [x] Print mode is supported or explicitly rejected with `UNSUPPORTED_RENDER_MODE`/equivalent typed error.
- [x] Student leak-prevention tests cover question answers, explanations, and teacher-only fields.
- [x] Golden snapshots cover representative worksheet and drill inputs.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md

## Implementation

- Added `packages/renderer/src/plugins/worksheet.ts` with complete plugin metadata, Zod boundary schema, base sanitizer policy, and `pages/worksheet` template routing.
- Added `packages/renderer/src/plugins/drill.ts` with complete plugin metadata, Zod boundary schema, quiz sanitizer policy for radio controls, and `pages/drill` template routing.
- Registered both plugins in `packages/renderer/src/core/runtime.ts` so `render({ kind: "worksheet" | "drill" })` works through the new kernel registry.
- Added `packages/renderer/__tests__/practice-plugins.test.ts` covering metadata, standalone output, print mode, validation failures, student answer/explanation leak prevention, and teacher-only filtering.
- Added representative Vitest snapshots for worksheet and drill student preview output.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/practice-plugins.test.ts -u` passed and wrote 2 snapshots.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/practice-plugins.test.ts __tests__/quiz-plugin.test.ts __tests__/core-renderer-kernel.test.ts` passed: 18 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` reported no diagnostics for `packages/renderer/src/plugins/worksheet.ts`, `packages/renderer/src/plugins/drill.ts`, `packages/renderer/src/core/runtime.ts`, and `packages/renderer/__tests__/practice-plugins.test.ts`.
- Manual library-surface check rendered `worksheet` and `drill` from `packages/renderer/dist/renderer.js` in print mode; both returned matching manifests, contained print CSS, and did not leak answers, explanations, or teacher-only prompts.
- Post-write size check: `worksheet.ts` 70 pure LOC, `drill.ts` 71, `runtime.ts` 9, `practice-plugins.test.ts` 98.

Note: focused renderer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags.
