---
title: Decomposition memory — template cache and teacher preferences
status: ready-for-agent
labels: [ready-for-agent]
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

- [ ] `DecompositionFeedback` is captured at approval/edit with a structured diff, persisted on a real DB.
- [ ] The template cache stores the approved (post-edit) sequence, not the raw LLM proposal, keyed by `(topic_normalized, grade, subject, locale)`.
- [ ] A per-teacher preference profile is updated from diffs and is retrievable.
- [ ] `unit_planner` retrieves template + preference priors when present and adapts (output reflects the prior but is not a verbatim copy).
- [ ] Priors are strictly soft: a retrieved template still passes through the validator, gate, and confidence checks; a teacher can ignore it.
- [ ] Templates/preferences are scoped per teacher.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [ ] `services/gateway/tests/test_decomposition_feedback.py`: approving an edited sequence persists a diff with the correct `edit_types`.
- [ ] `services/gateway/tests/test_template_cache.py`: an approved sequence becomes a retrievable template under the normalized key; the raw proposal is not stored.
- [ ] `packages/agents/tests/test_planner_priors.py`: with a matching template present, `unit_planner` produces a sequence structurally close to it yet persona-adapted; with no template, it plans cold.
- [ ] `services/gateway/tests/test_teacher_preferences.py`: repeated "split shorter" edits shift the teacher's preferred session length aggregate.
- [ ] Soft-prior test: a template that would violate CLT for the current persona is still corrected by the validator (no bypass).
- [ ] Run `uv run pytest services/gateway/tests/test_decomposition_feedback.py services/gateway/tests/test_template_cache.py packages/agents/tests/test_planner_priors.py services/gateway/tests/test_teacher_preferences.py -v`.

## Blocked by

- .scratch/topic-decomposition/006-unit-planner-agent.md
- .scratch/topic-decomposition/007-stage-wiring-and-unit-gate.md
