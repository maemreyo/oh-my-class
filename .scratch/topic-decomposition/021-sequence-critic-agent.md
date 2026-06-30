---
title: sequence_critic — adversarial pedagogy review of the proposed sequence
status: done
labels: []
created: 2026-06-30
---

## What to build

Add an independent adversarial reviewer of the proposed `LessonSequence` that catches **semantic pedagogy** errors the deterministic validator cannot (ADR-017 §Sub-agents). The validator (issue 003) checks structure (DAG/CLT/Bloom); the critic checks meaning.

`packages/agents/sub_agents/sequence_critic/`:

- Invoked inside the `UNIT_PLANNING` stage: `unit_planner → sequence_critic → bounded self-repair → SequenceConsistencyValidator`.
- Prompted to **refute** the sequence's pedagogy with a different lens: wrong prerequisite ordering, a split that fragments a single concept, a missing core sub-concept, redundant re-teaching across sessions, difficulty that does not build. Returns structured `SequenceCritique[]` (type, involved `session_id`s, severity, suggested fix).
- HARD critiques feed the bounded self-repair loop (reuse the existing recovery pattern); residual critiques are attached to the sequence and surfaced on the unit gate for the teacher.
- LLM via the existing transport (9router, model `4omc`); prompts via `PromptCompiler` + registry. No new framework/lib (`networkx` available for graph reasoning).

Gate behind `features.topic_decomposition_v1`. Bounded iterations to cap cost/latency.

## Acceptance criteria

- [x] `sequence_critic` runs after `unit_planner` and before the validator inside `UNIT_PLANNING`.
- [x] It returns structured `SequenceCritique[]` with type + involved sessions + severity + suggested fix.
- [x] HARD critiques trigger a bounded self-repair loop; residual critiques surface on the unit gate, not silently dropped.
- [x] Iterations are bounded (cost/latency cap); the stage always terminates with a sequence + any open critiques.
- [x] The critic is an independent deterministic lens, not the same call as `unit_planner`.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`.)

- [x] `packages/agents/tests/test_sequence_critic.py`: apply-before-remember yields an ordering critique.
- [x] same file: duplicate atomic sub-topic yields a fragmentation critique.
- [x] same file: HARD critique triggers bounded repair by Bloom rank.
- [x] Integration: `UNIT_PLANNING` attaches residual critiques to the gate payload.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/topic-decomposition/006-unit-planner-agent.md
