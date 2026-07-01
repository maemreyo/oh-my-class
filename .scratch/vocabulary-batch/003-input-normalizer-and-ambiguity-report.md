---
title: InputNormalizer and structured ambiguity report
status: done
labels: [ux, agents]
created: 2026-07-01
---

## What to build

Build a production-grade InputNormalizer capability for free-form teacher vocabulary input. Teachers should paste loose text, not learn Markdown/YAML. The normalizer outputs structured clusters, title hints, attached notes, parse confidence, ambiguous spans, clarifying questions, and skipped spans.

The normalizer must not directly interrupt the teacher. It returns a structured ambiguity report; the gateway/UI decides whether to continue automatically for high-confidence clusters, ask about low-confidence spans, or skip ambiguous clusters.

## Acceptance criteria

- [x] InputNormalizer accepts free-form mixed Vietnamese/English text and outputs `InputNormalizationReport`.
- [x] It extracts clusters, optional title hints, user notes, raw input spans, and confidence per cluster.
- [x] Low-confidence clusters produce clarifying questions without blocking high-confidence clusters.
- [x] Duplicate terms and overlapping clusters are flagged instead of silently merged when meaning could change.
- [x] The normalizer uses structured output validated by contracts and safe error summaries.
- [x] The UI/API can present ready clusters and ambiguous clusters separately.

## Detailed test suite

- [x] `packages/agents/tests/test_vocabulary_input_normalizer.py`: parses slash/comma/space-separated clusters and Vietnamese title hints.
- [x] `packages/agents/tests/test_vocabulary_input_normalizer.py`: attaches free-form notes to the intended cluster.
- [x] `packages/agents/tests/test_vocabulary_input_normalizer.py`: ambiguous spans produce clarifying questions and do not block ready clusters.
- [x] `packages/agents/tests/test_vocabulary_input_normalizer.py`: structured output validation fails closed on malformed LLM output.
- [x] `apps/web/tests/vocabulary-batch-normalization.test.tsx`: preview UI shows ready and ambiguous clusters separately.

## Verification

- `uv run pytest packages/agents/tests/test_vocabulary_input_normalizer.py common/contracts/tests/test_vocabulary_batch_contracts.py -q` → 10 passed.
- `pnpm --filter @oh-my-class/web test -- tests/vocabulary-batch-normalization.test.tsx` → web test suite passed, including the normalization preview test.
- `uv run python scripts/generate_zod_schemas.py` regenerated vocabulary batch schemas with structured ready/ambiguous cluster shapes.
- `uv run python scripts/verify_schema_parity.py` → all schemas in sync.

## Blocked by

- `001-contracts-and-methodology-mode.md`
