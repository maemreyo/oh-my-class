---
title: Decommission legacy renderer paths after registry migration
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Delete obsolete renderer paths and verify no code path can bypass the plugin registry, unified sanitizer, asset policy, or public API boundary.

## Acceptance criteria

- [x] `renderArtifactSync()` and regex-based `sanitizer.ts` are removed.
- [x] Public semantic-anchor and inverse-thinking wrapper exports are removed.
- [x] Old Artifact UI renderer API (`renderArtifactUi`, `renderArtifactUiSet`) removed from public exports (still accessible from source for baseline tests).
- [x] No production caller deep-imports renderer internals.
- [x] No `default -> lessonData()` fallback or equivalent silent routing remains (`renderAgentArtifact` migrated to `render()` API with explicit kind routing for all artifact types).
- [x] Full renderer test suite, TypeScript build, and quality gates pass.

## Implementation notes

- Deleted `packages/renderer/src/sanitizer.ts` (regex-based legacy sanitizer). It was used only by the removed `renderArtifactSync()`.
- Removed from `packages/renderer/src/renderer.ts`:
  - `renderArtifactSync` function and its `sanitizeHtml` import
  - `renderSemanticAnchorProjection` and `renderSemanticAnchorProjectionSet` exports
  - `renderArtifactUi` and `renderArtifactUiSet` exports
  - Corresponding type exports (`SemanticAnchorProjectionAudience`, `ArtifactUiRenderRequest`, etc.)
- Removed from `__tests__/renderer.test.ts`:
  - `renderArtifactSync (legacy)` describe block (9 tests)
  - `sanitizeHtml` describe block (9 tests)
  - Legacy imports (`renderArtifactSync`, `sanitizeHtml` from `../src/sanitizer.js`)
- `renderArtifact()` (async, uses Eta templates and new sanitizer) is retained as it is still used in template-library and other integration tests.
- Fixed additional bugs discovered during migration:
  - `active_recall_prompt` student projection in `lesson.ts` and `agent-component-projection.ts` incorrectly stripped `reveal_answer` (student-facing); only `teacher_rationale` should be stripped.
  - `quiz` answer fallback in `agent-renderer.ts` changed to `"—"` to satisfy `z.string().min(1)` schema when artifact has no answer field.
  - `roleplay_script` template test expectation updated to reflect deliberate omission of `answer_key` from student lesson view.
  - `active_recall_prompt.html` template: `Math.random()` replaced with deterministic slug from instruction text for stable snapshot testing.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run` — 413 tests passed (50 files, was 398 before issues 012/013/015 tests were added).
- `pnpm --filter @oh-my-class/renderer build` — clean TypeScript build.
- No production code outside `packages/renderer` references any removed function (verified via grep).

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 015-quality-gates-ci.md
