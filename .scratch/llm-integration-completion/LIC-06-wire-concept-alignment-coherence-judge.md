---
title: "Wire concept_alignment into practice QA and coherence_judge into unit_planner validation"
status: ready-for-agent
labels: [llm-integration, dark-code, quality]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 6
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0c. Both are real, tested, zero-caller modules with clear integration points — not an architecture decision, just wiring.

## What to build

Two independently-wireable modules:

1. **`verify_concept_alignment_with_majority`** (`packages/agents/concept_alignment.py:80`) checks whether a practice question is correctly assigned to its Knowledge Component, using a majority-vote LLM check. Zero production callers. Wire it into `practice_generator`'s question-generation flow (`packages/agents/sub_agents/practice_generator/semantic_anchor.py`) as a pre-publish QA gate: run it on generated questions before they're included in a `PracticeSet`, and route failures through the same failure-class handling `vocabulary_batch_orchestrator.py` already uses (`teacher_review`/`retry_then_fail`/`fail_cluster`).

2. **`run_coherence_lint`** (`packages/agents/quality/unit_coherence.py`, re-exported by `packages/agents/sub_agents/coherence_judge/__init__.py`) is an advisory, non-LLM lint checking cross-session coherence within a unit. Zero production callers. Wire it as a non-blocking validation step after `unit_planner_node` produces a `LessonSequence` — log/surface `CoherenceWarning`s (its own name implies "advisory," so it should not hard-fail the pipeline unless the product decision changes later).

## Acceptance criteria

- [ ] `verify_concept_alignment_with_majority` is called for generated practice questions before they reach a teacher/student; failing questions are handled via an explicit failure path, not silently dropped or silently passed.
- [ ] `run_coherence_lint` runs after `unit_planner_node`; its warnings are surfaced (logged, attached to run metadata, or surfaced in the run's diagnostic output) without blocking the pipeline.
- [ ] Both symbols move from implicitly-dark to referenced-in-`test_no_dark_runtime_modules.py`'s `REQUIRE_WIRED` (or removed from `KNOWN_DARK` if either was listed there).
- [ ] Existing unit tests for both modules (already passing per audit) are joined by an integration test proving the new caller actually invokes them.

## Blocked by

Nothing.
