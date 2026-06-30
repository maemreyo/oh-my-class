---
title: Decomposition memory — template cache and teacher preferences
status: done
labels: []
created: 2026-06-30
---

## What to build

Let the system learn from what teachers actually approve, so future decompositions improve (ADR-017 §Decomposition memory). All learned signals are **soft priors** — they bias `unit_planner`, never override the validator, gate, or confidence checks.

- **Edit-diff capture**: at unit-gate approval (and content-gate edits), persist a structured `DecompositionFeedback { proposed_vs_approved, edit_types[], session_id }`.
- **Template cache**: persist the **post-edit approved** sequence keyed by `(topic_normalized, grade, subject, locale)`. Future same-key requests retrieve it as a strong prior; the LLM adapts it to the current persona rather than planning cold.
- **Teacher preference profile**: per-teacher aggregates learned from diffs (typical session length, favored methodology by Bloom, split/merge tendency).
- These join grounding (issue 005) and persona (issue 013) as the four soft priors into `unit_planner` (issue 006).
- **Scope/governance**: templates and preferences are per-teacher by default; cross-teacher/org sharing is out of scope (future, vetted).

## Acceptance criteria

- [x] `DecompositionFeedback` is captured at approval/edit with a structured diff, persisted on a real DB model/store.
- [x] The template cache stores the approved (post-edit) sequence, not the raw LLM proposal, keyed by `(topic_normalized, grade, subject, locale)`.
- [x] A per-teacher preference profile is updated from diffs and is retrievable.
- [x] `unit_planner` retrieves template + preference priors when present and adapts (output reflects the prior but is not a verbatim copy).
- [x] Priors are strictly soft: a retrieved template still passes through the validator, gate, and confidence checks; a teacher can ignore it.
- [x] Templates/preferences are scoped per teacher.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [x] `services/gateway/decomposition_memory.py` captures edit types and approved template rows.
- [x] Approved sequence becomes a retrievable template under the normalized key; raw proposal remains in feedback history, not the template.
- [x] `packages/agents/tests/test_planner_priors.py`: teacher preference prior softly adapts the plan.
- [x] Preference profile updates preferred session duration aggregate.
- [x] Soft-prior test: sequence still passes through `SequenceConsistencyValidator` in `unit_planner_node`.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/topic-decomposition/006-unit-planner-agent.md
- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
