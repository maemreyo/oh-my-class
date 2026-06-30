---
title: sequence_critic — adversarial pedagogy review of the proposed sequence
status: ready-for-agent
labels: [ready-for-agent]
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

- [ ] `sequence_critic` runs after `unit_planner` and before the validator inside `UNIT_PLANNING`.
- [ ] It returns structured `SequenceCritique[]` with type + involved sessions + severity + suggested fix.
- [ ] HARD critiques trigger a bounded self-repair loop; residual critiques surface on the unit gate, not silently dropped.
- [ ] Iterations are bounded (cost/latency cap); the stage always terminates with a sequence + any open critiques.
- [ ] The critic is an independent lens (separate prompt/agent), not the same call as `unit_planner`.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`.)

- [ ] `packages/agents/tests/test_sequence_critic.py`: a sequence with an obviously wrong prerequisite order (apply-before-remember) yields an ordering critique; a sound sequence yields none.
- [ ] same file: a sequence that splits one atomic concept across two sessions yields a fragmentation critique.
- [ ] `packages/agents/tests/test_sequence_critic_repair.py`: a HARD critique triggers a bounded repair; after the cap, the stage terminates with residual critiques attached for the gate.
- [ ] Integration: `unit_planner → critic → validator` produces a sequence that passes both the critic (no HARD residual) and the validator for a clean golden topic.
- [ ] Run `uv run pytest packages/agents/tests/test_sequence_critic*.py -v`.

## Blocked by

- .scratch/topic-decomposition/006-unit-planner-agent.md
