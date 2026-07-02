---
title: Add renderer rewrite quality gates to CI
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Add the required quality gate suite for the rewritten renderer: registry completeness, golden snapshots, leak-prevention invariant, sanitizer XSS corpus, worker protocol tests, and visual/print smoke.

## Acceptance criteria

- [x] Registry completeness fails if any of the 12 existing artifact types or required Artifact UI kinds lacks a plugin.
- [x] Golden snapshot comparisons use the Phase 0 current-renderer baselines (regenerated after root-cause-session template update in issue 011).
- [x] Leak-prevention invariant runs against student-capable lesson plugin.
- [x] XSS corpus runs against sanitizer policies (base, quiz, lesson configs).
- [x] Worker protocol contract tests run (existing `__tests__/worker-protocol-v2.test.ts`).
- [x] Visual/print smoke tests added in `__tests__/i18n-print-visual-smoke.test.ts`.

## Implementation notes

- Created `packages/renderer/__tests__/quality-gates.test.ts` (13 tests) covering:
  - **Registry completeness**: asserts all 12 standard artifact kinds, 3 Artifact UI kinds, and required metadata fields are present.
  - **Teacher-content leak prevention**: lesson rendered with student audience must not contain `explain`, `wrong_reasons`, or `teacher_only` section content.
  - **XSS corpus**: `sanitizeRenderedHtml` tested against `<script>`, `javascript:` href, `onerror`, `<iframe>`, `<svg onload>`, with both base and quiz/lesson configs.
  - **Valid standalone HTML**: quiz rendered for student produces `<!DOCTYPE html>`, no external URLs.
- Regenerated `__tests__/current-renderer-baselines.test.ts` baselines with `UPDATE_CURRENT_RENDERER_BASELINES=1` after root-cause-session template change.
- Also added `active_recall_prompt` student projection fix: `reveal_answer` is kept for students (the reveal button requires it); only `teacher_rationale` is stripped.
- Fixed `active_recall_prompt.html` template to use deterministic ID from instruction text (replaced `Math.random()`) to enable stable snapshot tests.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/quality-gates.test.ts` — 13 tests passed.
- `pnpm --filter @oh-my-class/renderer exec vitest run` — 413 tests passed (50 files).
- `pnpm --filter @oh-my-class/renderer build` — clean TypeScript build.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 012-i18n-print-and-visual-qa.md
- 014-public-api-boundary-and-caller-migration.md
