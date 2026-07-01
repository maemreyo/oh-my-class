---
title: Reusable Researcher lexical grounding profile
status: done
labels: [ready-for-agent, agents, research]
created: 2026-07-01
---

## What to build

Reuse the existing Researcher capability for dictionary-grounded lexical distinctions. Add a `lexical_grounding` profile that receives normalized clusters and returns source-informed definitions, usage constraints, contrast notes, edge cases, confidence, and teacher-only source notes.

This is not a new bespoke SemanticAnchorResearchAgent. It is a reusable Researcher profile with a vocabulary-specific request/response contract.

## Acceptance criteria

- [x] Researcher can run a `lexical_grounding` profile without changing normal lesson research behavior.
- [x] Lexical grounding output includes term definitions, source notes, usage constraints, common confusions, examples/counterexamples, confidence, and uncertainty flags.
- [x] Source notes are teacher-facing only and never required in student projections.
- [x] Insufficient sources produce `needs_review`-ready uncertainty, not confident invented distinctions.
- [x] Grounding results are cacheable by cluster snapshot and reusable term-distinction keys.

## Detailed test suite

- [x] `packages/agents/tests/test_researcher_lexical_grounding.py`: lexical grounding for `travel / journey / trip / voyage / excursion` returns source notes and confidence.
- [x] `packages/agents/tests/test_researcher_lexical_grounding.py`: ordinary `post_blueprint_research` output is unchanged for `generate_pack` mode.
- [x] `packages/agents/tests/test_lexical_grounding_uncertainty.py`: insufficient or conflicting evidence yields uncertainty flags.
- [x] `packages/agents/tests/test_lexical_grounding_cache_keys.py`: term-distinction cache keys are deterministic.

## Verification

- `uv run pytest packages/agents/tests/test_researcher_lexical_grounding.py packages/agents/tests/test_lexical_grounding_uncertainty.py packages/agents/tests/test_lexical_grounding_cache_keys.py common/contracts/tests/test_vocabulary_batch_contracts.py -q` → `11 passed`.
- `uv run python scripts/generate_zod_schemas.py` → success.
- `uv run python scripts/verify_schema_parity.py` → all schemas in sync, including `SemanticAnchorCluster`.

## Blocked by

- `001-contracts-and-methodology-mode.md`
- `003-input-normalizer-and-ambiguity-report.md`
