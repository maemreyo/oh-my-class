---
title: "Wire concept_alignment into practice QA and coherence_judge into unit_planner validation"
status: done
labels: [llm-integration, dark-code, quality]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 6
---

> **Done, partially (2026-07-08).** `run_coherence_lint` wired as designed — see below.
> `verify_concept_alignment_with_majority` was **not** wired: on inspection, this
> issue's premise ("clear integration point," not just an architecture decision)
> didn't hold. `verify_concept_alignment_with_majority` needs a question tagged
> with an assigned KC id/description + sibling KCs; `practice_generator/semantic_anchor.py`'s
> `StudentPracticeItem` carries no KC association at all (`item_id`/`intent`/`prompt`
> only), and no other question/practice generator in the codebase produces
> KC-tagged questions either — `unit_planner` assigns KCs at the session level, not
> per-question. Wiring this in would have meant fabricating fake KC data just to
> make the call type-check, which is worse than leaving it honestly dark. Moved
> to `KNOWN_DARK` in `tests/test_no_dark_runtime_modules.py` with the reason
> recorded, instead of force-fitting a wrong integration.
>
> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0c.

## What to build

Two independently-wireable modules:

1. **`verify_concept_alignment_with_majority`** (`packages/agents/concept_alignment.py:80`) checks whether a practice question is correctly assigned to its Knowledge Component, using a majority-vote LLM check. Zero production callers. Wire it into `practice_generator`'s question-generation flow (`packages/agents/sub_agents/practice_generator/semantic_anchor.py`) as a pre-publish QA gate: run it on generated questions before they're included in a `PracticeSet`, and route failures through the same failure-class handling `vocabulary_batch_orchestrator.py` already uses (`teacher_review`/`retry_then_fail`/`fail_cluster`).

2. **`run_coherence_lint`** (`packages/agents/quality/unit_coherence.py`, re-exported by `packages/agents/sub_agents/coherence_judge/__init__.py`) is an advisory, non-LLM lint checking cross-session coherence within a unit. Zero production callers. Wire it as a non-blocking validation step after `unit_planner_node` produces a `LessonSequence` — log/surface `CoherenceWarning`s (its own name implies "advisory," so it should not hard-fail the pipeline unless the product decision changes later).

## Acceptance criteria

- [ ] `verify_concept_alignment_with_majority` is called for generated practice questions — **not done**, no KC-tagged question generator exists to call it from (see done-note). Needs its own issue once/if a KC-tagged question generator is built; tracking that as a prerequisite, not re-litigating it here.
- [x] `run_coherence_lint` runs after `unit_planner_node` (`packages/agents/sub_agents/unit_planner/nodes.py`); warnings are attached to the node's return dict as `coherence_warnings` (list of serialized `CoherenceWarning`), non-blocking — `unit_planner_node` still returns its `lesson_sequence` regardless of warnings.
- [x] `run_coherence_lint` moved from `KNOWN_DARK` to `REQUIRE_WIRED` in `tests/test_no_dark_runtime_modules.py`. `verify_concept_alignment_with_majority` added fresh to `KNOWN_DARK` (was in neither list before) with the reason recorded.
- [x] `packages/agents/tests/test_unit_planner.py` (7 tests) passes unchanged with the new field added; `tests/test_no_dark_runtime_modules.py` passes with the updated ledger.

## Blocked by

Nothing.
