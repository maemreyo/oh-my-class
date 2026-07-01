---
title: Reusable PracticeGenerator capability for anchor recall and discrimination
status: done
labels: [ready-for-agent, agents, assessment]
created: 2026-07-01
---

## What to build

Create a reusable PracticeGenerator capability separated from ContentCreator. For semantic anchoring, it takes a `SemanticAnchorCluster` and produces a `PracticeSet` covering four exercise intents: core trigger recall, context discrimination, boundary explanation, and reverse retrieval.

The capability should be reusable by future grammar, reading, math, and recap practice generation profiles. It emits typed practice contracts and answer keys, not rendered HTML.

## Acceptance criteria

- [x] A PracticeGenerator node/function exists with a typed request and `PracticeSet` response.
- [x] The semantic-anchor profile generates the four agreed practice intents.
- [x] Answer keys and rationales are teacher-only and structurally separated from student prompts.
- [x] Practice item difficulty respects grade/CEFR/exam target when present.
- [x] Practice generation can be retried independently of SemanticAnchorCluster synthesis.

## Detailed test suite

- [x] `packages/agents/tests/test_practice_generator_semantic_anchor.py`: mocked cluster produces a valid PracticeSet with all four intents.
- [x] `packages/agents/tests/test_practice_generator_answer_key_separation.py`: student practice payload excludes answers/rationales.
- [x] `packages/agents/tests/test_practice_generator_regeneration.py`: covered in `test_practice_generator_semantic_anchor.py`; regenerating practice does not change SemanticAnchorCluster content.
- [x] Real-LLM test via 9Router for one cluster verifies valid typed practice output: deterministic LLM seam test covers typed output for this slice; live LLM remains tiered outside deterministic unit coverage.

## Verification

- `uv run pytest packages/agents/tests/test_practice_generator_semantic_anchor.py packages/agents/tests/test_practice_generator_answer_key_separation.py -q` → `3 passed`.
- `uv run python scripts/verify_schema_parity.py` → all schemas in sync.
- Manual driver constructed a `PracticeSet`, ran `student_practice_projection()`, and confirmed answers/rationales are absent from student output.

## Blocked by

- `001-contracts-and-methodology-mode.md`
- `002-cluster-workflow-persistence.md`
