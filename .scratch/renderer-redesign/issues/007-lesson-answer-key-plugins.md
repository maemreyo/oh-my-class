---
title: Migrate lesson and answer_key plugins with audience safety
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `lesson` and `answer_key` into plugins with explicit audience policies. Student lesson rendering must strip teacher-only data; answer key rendering must remain controlled and never appear through a student lesson path.

## Acceptance criteria

- [x] `lesson` and `answer_key` plugins declare complete plugin metadata, schemas, capabilities, and sanitizer policies.
- [x] Student `lesson` output removes teacher-only fields and passes leak-prevention invariants.
- [x] `answer_key` plugin declares appropriate audience support and sanitizer policy.
- [x] Existing paper-dossier lesson/answer-key behavior is represented as plugin behavior or intentionally superseded by the new plugin design.
- [x] Golden snapshots cover teacher/student-relevant cases and print where supported.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
- 005-practice-plugins.md

## Implementation

- Added `packages/renderer/src/plugins/lesson.ts` with complete plugin metadata, Zod boundary schema, print capability, and `pages/lesson` template routing.
- Added `packages/renderer/src/plugins/answer-key.ts` with complete plugin metadata, Zod boundary schema, teacher-only audience support, print capability, and `pages/answer_key` template routing.
- Registered both plugins in `packages/renderer/src/core/runtime.ts` so `render({ kind: "lesson" | "answer_key" })` works through the default registry.
- Extended `packages/renderer/src/core/sanitizer.ts` and `packages/renderer/src/core/types.ts` so the new kernel can select the existing answer-key sanitizer policy; lesson uses the quiz-compatible policy because lesson components include controls already covered by that allowlist.
- Added student-safe lesson projection in the plugin adapter for `question_card`, `question_list`, `roleplay_script`, `active_recall_prompt`, and `contrastive_pairs` teacher-only fields.
- Added `packages/renderer/__tests__/lesson-answer-key-plugins.test.ts` covering metadata, student lesson leak prevention, teacher-only answer-key rendering, student answer-key rejection, print mode, and representative snapshots.
- Existing paper-dossier lesson/answer-key wrappers remain in place until Issue 014 caller migration; plugin behavior intentionally uses the standard `pages/lesson` and `pages/answer_key` templates as the new registry path.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/lesson-answer-key-plugins.test.ts -u` passed and wrote 2 snapshots.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/lesson-answer-key-plugins.test.ts __tests__/summary-visual-plugins.test.ts __tests__/practice-plugins.test.ts __tests__/quiz-plugin.test.ts __tests__/core-policy.test.ts __tests__/core-renderer-kernel.test.ts` passed: 33 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` reported no diagnostics for `packages/renderer/src/plugins/lesson.ts`, `packages/renderer/src/plugins/answer-key.ts`, `packages/renderer/src/core/types.ts`, `packages/renderer/src/core/sanitizer.ts`, `packages/renderer/src/core/runtime.ts`, and `packages/renderer/__tests__/lesson-answer-key-plugins.test.ts`.
- Manual library-surface check rendered `lesson` and `answer_key` from `packages/renderer/dist/renderer.js` in print mode; student lesson did not leak answers, reveal text, rationale, or teacher-only section content; teacher answer key displayed the explanation; student answer-key render failed with `unsupported_audience`; both outputs contained print CSS.
- Post-write size check: `core/types.ts` 97 pure LOC, `core/sanitizer.ts` 43, `lesson.ts` 115, `answer-key.ts` 50, `runtime.ts` 13, `lesson-answer-key-plugins.test.ts` 129.

Note: focused renderer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags.
