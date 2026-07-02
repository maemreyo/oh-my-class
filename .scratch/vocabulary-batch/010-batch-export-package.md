---
title: Status-aware batch export package with offline index
status: done
labels: [ready-for-agent, export, renderer]
created: 2026-07-01
---

## What to build

Export vocabulary batch outputs as a standalone offline package. The package includes an `index.html`, per-cluster teaching/practice projections, optional practice GIFT/H5P exports, and `manifest.json` describing cluster statuses and file refs.

Export is status-aware: `passed` clusters export teacher and student files; `needs_review` clusters export teacher review files only until approved; `failed` clusters export diagnostics only.

## Acceptance criteria

- [x] Batch ZIP contains offline `index.html`, `manifest.json`, and per-cluster folders.
- [x] `index.html` lists clusters, terms, status, warnings, and links to available files.
- [x] Passed clusters include teaching teacher/student and practice teacher/student HTML.
- [x] Needs-review clusters withhold student/practice/LMS exports until teacher approval.
- [x] Failed clusters include diagnostics only and are clearly marked in the index.
- [x] Optional GIFT/H5P exports are generated only from student-safe PracticeSet data.
- [x] Export uses existing ExporterRegistry/packager patterns and fails closed on unsupported formats.

## Detailed test suite

- [x] `packages/exporters/__tests__/vocabulary-batch.test.ts`: ZIP structure contains expected index, manifest, and cluster files.
- [x] `packages/exporters/__tests__/vocabulary-batch.test.ts`: passed/needs_review/failed statuses produce correct file sets.
- [x] `packages/exporters/__tests__/vocabulary-batch.test.ts`: GIFT/H5P export uses PracticeSet and excludes teacher-only data.
- [x] `packages/exporters/__tests__/vocabulary-batch.test.ts`: offline index has no external assets and links valid local files.

## Completion notes

- Added `packages/exporters/src/vocabulary-batch/index.ts` with `buildVocabularyBatchPackage()`.
- Added `packages/exporters/src/vocabulary-batch/cli.ts` and `services/gateway/vocabulary_batch_export.py` so the Python gateway can invoke the TypeScript packager instead of duplicating ZIP logic.
- The ZIP package includes root `index.html`, `manifest.json`, and `clusters/<cluster-id>/...` files.
- Status policy:
  - `passed` and teacher-approved `needs_review` clusters export teacher/student teaching + practice HTML and optional LMS files.
  - unapproved `needs_review` clusters export teacher HTML only.
  - `failed` clusters export diagnostics only.
- GIFT/H5P are generated only from `PracticeSet` prompts/answers and do not include teacher scripts, source notes, or rationales.
- Verified with focused Vitest, TypeScript build, gateway bridge tests, LSP diagnostics, and a manual Node ZIP smoke check.
- `uv run pytest services/gateway/tests/test_vocabulary_batch_export.py -q` → 2 passed.
- `pnpm --filter @oh-my-class/exporters test -- vocabulary-batch-cli.test.ts vocabulary-batch.test.ts` → 52 passed.

## Blocked by

- `007-vocabulary-batch-orchestrator.md`
- `008-semantic-anchoring-quality-gate.md`
- `009-projections-and-structured-editor.md`
