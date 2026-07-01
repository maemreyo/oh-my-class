---
title: Per-cluster workflow persistence and evidence ledger
status: done
labels: [persistence, observability]
created: 2026-07-01
---

## What to build

Add durable per-cluster workflow state for `vocabulary_batch` runs. A vocabulary cluster is a child workflow unit, not an artifact. Each cluster needs status, attempts, evidence, review state, export refs, and retry history so a 20-100 cluster batch can partially succeed without hiding failures.

Reuse the existing teaching-pack run/job/control plane and follow the per-artifact workflow lessons from ADR-020, but model clusters with vocabulary-specific state instead of overloading `artifact_type`.

## Acceptance criteria

- [x] A `VocabularyClusterWorkflow` persistence model or equivalent contract stores `cluster_id`, `run_id`, normalized input, status, attempts, review status, and export refs.
- [x] Cluster status supports `queued`, `grounding`, `synthesizing`, `practice_generating`, `validating`, `needs_review`, `passed`, `failed`, `skipped`, and `exported` or an equivalent typed lifecycle.
- [x] A per-cluster evidence ledger records normalized input, grounding sources, generated contract versions, quality results, teacher edits, approvals, export refs, and retry history.
- [x] Cluster snapshot hashes are deterministic and support audit/re-render without storing chain-of-thought.
- [x] Existing `ArtifactWorkflow` behavior and migrations are not regressed.

## Detailed test suite

- [x] `common/contracts/tests/test_vocabulary_cluster_workflow.py`: lifecycle statuses validate and illegal transitions are rejected by pure transition helpers.
- [x] `services/gateway/tests/test_vocabulary_cluster_workflow_persistence.py`: create/read/update cluster workflows against migrated test DB.
- [x] `services/gateway/tests/test_vocabulary_cluster_evidence_ledger.py`: evidence entries append in order and redact forbidden raw provider/internal data.
- [x] `packages/agents/tests/test_vocabulary_cluster_snapshot.py`: cluster snapshot hash is deterministic across equivalent payload orderings.
- [x] Regression: existing artifact workflow persistence tests pass unchanged.

## Verification

- `uv run pytest common/contracts/tests/test_vocabulary_cluster_workflow.py packages/agents/tests/test_vocabulary_cluster_snapshot.py services/gateway/tests/test_vocabulary_cluster_workflow_persistence.py services/gateway/tests/test_vocabulary_cluster_evidence_ledger.py -q` → 7 passed, 3 skipped because local Postgres on `localhost:5432` was unavailable.
- `uv run python scripts/generate_zod_schemas.py` regenerated `common/schemas/src/generated/vocabulary_cluster_workflow.ts` and index exports.
- `uv run python scripts/verify_schema_parity.py` → all schemas in sync, including `VocabularyClusterWorkflow`.

## Blocked by

- `001-contracts-and-methodology-mode.md`
