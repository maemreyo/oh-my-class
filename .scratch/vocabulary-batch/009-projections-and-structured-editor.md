---
title: Teacher/student projections and structured field editor
status: done
labels: [ready-for-agent, frontend, renderer]
created: 2026-07-01
---

## What to build

Render separate teacher and student projections for teaching and practice. Teacher projection is the student view plus annotations; student projection contains only student-safe content. Add a structured field editor so teachers can edit contract fields and re-render, rather than editing HTML directly.

The UI must be user-centric for batch review: cluster list, statuses, warning banners, preview panes, field-level editing, approve/regenerate/skip actions, and no accidental student export from `needs_review` clusters.

## Acceptance criteria

- [x] Renderer builds separate teaching teacher/student HTML and practice teacher/student HTML from the same contracts.
- [x] Teacher projection includes scripts, source notes, edge cases, review flags, and answer rationales where appropriate.
- [x] Student projection excludes teacher scripts, source notes, answer keys, and internal confidence details.
- [x] Structured field editor edits contract fields and revalidates before re-render.
- [x] Teacher approval can unlock a `needs_review` cluster for the current run; optional edits save per-teacher preference events.
- [x] Existing content approval preview patterns are reused where practical.

## Detailed test suite

- [x] `packages/renderer/__tests__/semantic-anchor-projections.test.ts`: teacher projection contains annotations; student projection does not.
- [x] `packages/renderer/__tests__/semantic-anchor-projections.test.ts`: all generated HTML is standalone and has no external URLs.
- [x] `apps/web/tests/vocabulary-batch-review.test.tsx`: teacher can edit a field, re-render preview, and approve a cluster.
- [x] `apps/web/tests/vocabulary-batch-review.test.tsx`: `needs_review` cluster clearly shows withheld student export.
- [x] INVARIANT-05 regression: student files contain no answer key/teacher rationale strings.

## Completion notes

- Added `packages/renderer/src/semantic-anchor-projections.ts` and exported it from the renderer entrypoint.
- Added teacher/student teaching/practice projections from `SemanticAnchorCluster` + `PracticeSet` with standalone offline HTML and student-safe redaction.
- Added `apps/web/src/components/vocabulary-batch-review-editor.tsx` for cluster list, status/warnings, preview panes, field-level edits, approve/regenerate/skip actions, and `needs_review` student-export withholding.
- Re-exported semantic anchor generated types from `common/schemas/src/index.ts` for app/renderer consumers.
- Verified focused renderer/web tests and renderer build; web typecheck is blocked only by the pre-existing `artifactStatuses` undefined error in `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx`.

## Blocked by

- `005-semantic-anchor-synthesis.md`
- `006-practice-generator-capability.md`
- `008-semantic-anchoring-quality-gate.md`
