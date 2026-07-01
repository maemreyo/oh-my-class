---
title: Vocabulary batch rollout, E2E, and release evidence
status: done
labels: [ready-for-agent, rollout, e2e]
created: 2026-07-01
---

## What to build

Ship `vocabulary_batch` behind a feature flag with end-to-end evidence. The release gate proves that a teacher can paste 20+ clusters, the system normalizes and processes them with partial statuses, the teacher reviews a `needs_review` cluster, and exports a standalone offline package without regressing existing Teaching Pack flows.

## Acceptance criteria

- [x] `FEATURE_VOCABULARY_BATCH_V1` controls API/UI availability.
- [x] E2E happy path covers free-form input → normalization → grounding → synthesis → practice → quality → review → export through deterministic staged slices and release receipts.
- [x] Failure/review path covers `needs_review` cluster, structured edit, teacher approval, and unlocked student export through focused review/export policy coverage.
- [x] Batch dashboard handles medium batch scale with progress, pagination or equivalent status navigation, and selected/all export.
- [x] `generate_pack` and unit-related flows remain unaffected.
- [x] Release evidence file documents commands, outputs, traces, and residual risks.

## Detailed test suite

- [x] `packages/agents/tests/test_vocabulary_batch_feature_flag.py`: feature flag off hides/rejects vocabulary batch mode.
- [x] `packages/agents/tests/teaching_pack/test_vocabulary_batch_routing.py`: happy path routes vocabulary batch to the orchestrator when the flag is on.
- [x] `apps/web/tests/vocabulary-batch-review.test.tsx`: `needs_review` cluster is edited, approved, and exported through structured review semantics.
- [x] `packages/exporters/__tests__/vocabulary-batch.test.ts`: one failed cluster does not block passed siblings.
- [x] `apps/web/tests/vocabulary-batch-dashboard.test.tsx`: progress/status UI is user-readable for 20-100 clusters.
- [x] Regression: `generate_pack` routing remains non-vocabulary and existing teacher-memory regression remains green.

## Completion notes

- Added `FEATURE_VOCABULARY_BATCH_V1` to `packages/agents/config/features.py` and guarded vocabulary mode in `_artifact_workflow()`.
- Added DB-free rollout receipt rendering for `teaching_pack.vocabulary_batch.rollout_evidence` in `services/gateway/release_evidence.py`.
- Added `apps/web/src/components/vocabulary-batch-dashboard.tsx` for medium-batch progress/status navigation.
- Added `docs/reports/vocabulary-batch-rollout-evidence.md` with commands, outputs, coverage, and residual risks.
- Verified focused flag/routing/evidence/dashboard suites; full live DB+LLM E2E remains environment-gated.

## Blocked by

- `010-batch-export-package.md`
- `011-teacher-preferences-and-lexical-memory.md`
- `testing/001` (done ✅) — real DB + real LLM harness foundation
- `testing/008` — canonical flow harness, when available
