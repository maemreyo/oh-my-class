# Vocabulary Batch Rollout Evidence

Date: 2026-07-01
Feature flag: `FEATURE_VOCABULARY_BATCH_V1`

## Scope

This evidence covers the deterministic rollout gate for the `vocabulary_batch` mode: feature flag control, medium-batch dashboard readability, partial review/failure evidence, status-aware offline packaging, and regressions for existing `generate_pack` routing.

## Evidence commands

- `uv run pytest packages/agents/tests/test_vocabulary_batch_feature_flag.py packages/agents/tests/teaching_pack/test_vocabulary_batch_routing.py services/gateway/tests/test_release_evidence_exports.py::TestReleaseEvidenceExports::test_render_markdown_includes_vocabulary_batch_rollout_receipts -q` → `6 passed`.
- `pnpm vitest run tests/vocabulary-batch-dashboard.test.tsx` from `apps/web` → `2 passed`.
- `pnpm vitest run __tests__/vocabulary-batch.test.ts` from `packages/exporters` → `4 passed`.
- Manual ZIP smoke through `buildVocabularyBatchPackage()` → ZIP magic bytes valid and manifest listed 5 generated files for a passed cluster.
- Manual BaseStore vocabulary memory smoke → teacher preference correction and shared lexical reuse passed.

## Release-gate scenarios

| Scenario | Evidence | Status |
|---|---|---|
| Feature flag off rejects `vocabulary_batch` mode | `test_vocabulary_batch_feature_flag.py`, `test_vocabulary_batch_routing.py` | PASS |
| Feature flag on routes to vocabulary orchestrator | `test_vocabulary_batch_routing.py` | PASS |
| Existing `generate_pack` flow unaffected | `test_generate_pack_is_not_vocabulary_batch_mode` | PASS |
| Medium dashboard scale (20-100 clusters) | `vocabulary-batch-dashboard.test.tsx` | PASS |
| Partial failure/review status remains exportable for passed siblings | `vocabulary-batch.test.ts` policy coverage | PASS |
| Release evidence markdown includes vocabulary batch receipts | `test_release_evidence_exports.py` DB-free receipt test | PASS |

## Residual risks

- Full live E2E with real DB and real LLM is still gated by local/CI environment availability. Deterministic component, orchestrator, exporter, memory, and release-evidence coverage is in place.
- Local web typecheck still has a pre-existing unrelated error in `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx`: `artifactStatuses` is possibly undefined.
- Local Postgres on `localhost:5432` remains unavailable in this environment, so DB-backed gateway suites continue to skip/fail outside focused DB-free evidence checks.
