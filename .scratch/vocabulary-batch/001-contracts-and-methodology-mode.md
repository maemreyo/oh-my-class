---
title: Contracts and methodology mode for vocabulary batch
status: done
labels: [contracts, methodology]
created: 2026-07-01
---

## What to build

Add the source-of-truth contracts that make `vocabulary_batch` a real Teaching Pack mode and make Semantic Anchoring a selectable methodology without changing runtime behavior yet.

This slice establishes the typed vocabulary that later slices use: the run mode, semantic anchoring methodology metadata, batch config, normalization report, lexical grounding bundle, SemanticAnchorCluster, PracticeSet, projection references, and status enums. Contracts live in `common/contracts`; Zod codegen exposes them to the frontend. Practice remains a separate contract and must not be added as a new `ArtifactType`.

## Acceptance criteria

- [x] `PipelineMode` includes `vocabulary_batch` while existing modes remain backward-compatible.
- [x] `methodology_registry` includes a `semantic_anchoring` entry with Vietnamese label, required components, supported artifacts, and export formats.
- [x] Source-of-truth Pydantic contracts exist for `VocabularyBatchConfig`, `InputNormalizationReport`, `LexicalGroundingBundle`, `SemanticAnchorCluster`, `PracticeSet`, projection refs, cluster status, and export policy.
- [x] `PracticeSet` is a separate contract, not an `ArtifactType` and not nested inside `SemanticAnchorCluster`.
- [x] Generated Zod schemas include the new contracts and methodology tag.
- [x] Existing methodology and run-contract parity tests still pass.

## Detailed test suite

- [x] `common/contracts/tests/test_vocabulary_batch_contracts.py`: validates happy-path batch config, normalization report, lexical grounding bundle, SemanticAnchorCluster, PracticeSet, and projection refs.
- [x] `common/contracts/tests/test_vocabulary_batch_contracts.py`: rejects invalid cluster status, missing bilingual anchor fields, and malformed export policy.
- [x] `common/contracts/tests/test_methodology_registry.py`: semantic_anchoring appears with expected required components and compatibility rules.
- [x] `common/contracts/tests/test_run_contract.py`: `vocabulary_batch` validates without regressing existing modes.
- [x] `python scripts/generate_zod_schemas.py` and `python scripts/verify_schema_parity.py` pass.

## Verification

- `uv run pytest common/contracts/tests/test_vocabulary_batch_contracts.py common/contracts/tests/test_methodology_registry.py common/contracts/tests/test_run_contract_plan_unit.py -q` → 14 passed.
- `uv run python scripts/generate_zod_schemas.py` regenerated `common/schemas/src/generated/vocabulary_batch.ts`, `index.ts`, and `methodology_registry.ts`.
- `uv run python scripts/verify_schema_parity.py` → all schemas in sync, including `SemanticAnchorCluster`.

## Blocked by

None - can start immediately.
