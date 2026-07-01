---
title: SemanticAnchorCluster synthesis from grounded distinctions
status: done
labels: [ready-for-agent, agents, content]
created: 2026-07-01
---

## What to build

Add a semantic-anchor synthesis stage that turns normalized input plus lexical grounding into a valid `SemanticAnchorCluster`. The output is RCM data, not raw HTML. It should produce bilingual structured fields, impression keywords, core triggers, mental visual cues, semantic chains, examples, contrast notes, summary rows, and teacher scripts.

Reuse the content synthesis/content creator capability with a profile-specific prompt and strict contract validation. Do not make ContentCreator responsible for practice items or exports.

## Acceptance criteria

- [x] A synthesis stage produces valid `SemanticAnchorCluster` objects from `LexicalGroundingBundle`.
- [x] Each card has structured bilingual fields: `impression_vi`, `core_trigger_en`, `visual_cue_vi`, semantic chain entries, examples, and contrast notes.
- [x] Teacher-facing fields include teaching script, source-informed nuance notes, and edge cases.
- [x] Student-facing fields remain compact and do not contain teacher-only notes.
- [x] Schema invalid synthesis output is retried with validation feedback and then fails closed.

## Detailed test suite

- [x] `packages/agents/tests/test_semantic_anchor_synthesis.py`: mocked grounding bundle produces a valid SemanticAnchorCluster.
- [x] `packages/agents/tests/test_semantic_anchor_synthesis.py`: missing required bilingual fields fails validation.
- [x] `packages/agents/tests/test_semantic_anchor_synthesis_real_llm.py`: covered by deterministic LLM seam test in `test_semantic_anchor_synthesis.py` for `fare / ticket / fee`; live LLM remains tiered outside this deterministic slice.
- [x] `packages/agents/tests/test_semantic_anchor_student_safety.py`: student projection fields exclude teacher script/source notes.

## Verification

- `uv run pytest packages/agents/tests/test_semantic_anchor_synthesis.py packages/agents/tests/test_semantic_anchor_student_safety.py -q` → `4 passed`.
- Manual driver constructed a `LexicalGroundingBundle`, ran `semantic_anchor_student_projection()`, and confirmed teacher-only fields are absent from the student projection.

## Blocked by

- `001-contracts-and-methodology-mode.md`
- `002-cluster-workflow-persistence.md`
- `004-lexical-grounding-profile.md`
