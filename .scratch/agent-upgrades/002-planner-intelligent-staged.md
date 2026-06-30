---
title: Planner — staged backward-design, context-adaptive, learning
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Upgrade the single-lesson planner from single-shot JSON to an intelligent, context-adaptive pipeline (divide-and-conquer; no mega-prompt), mirroring `unit_planner` at lesson scale and sharing modules.

- **Staged backward-design (Curricular-CoT, focused sub-steps):** (1) transfer goal + enduring understandings → (2) prerequisites + misconceptions → (3) **assessment evidence first** → (4) objectives mapped to assessments + Bloom → (5) Gagné 9-event sequencing with cognitive-load awareness → emit `LessonPlan`.
- **Grounding:** consume the curriculum grounding source (age-band duration, Bloom distribution, prerequisite norms) by `(grade, subject, locale)`.
- **Single-lesson validator (sibling of `SequenceConsistencyValidator`)** HARD: Bloom ≥2, assessment↔objective alignment, prerequisite-before-apply ordering, cognitive-load, duration realism → bounded self-repair.
- **`lesson_critic` (sibling of `sequence_critic`)**: adversarial pre-gate check (objective↔assessment coverage, prerequisite gaps, missed misconceptions); shares the critic module, different lens.
- **Context-adaptive (the smart leap):** consume **3 sources** — declared persona (ClassProfile), taught (ClassKnowledgeGraph), learned (KT mastery) — to calibrate difficulty/pacing/assume-vs-reteach/depth; degrade to persona/grounding on cold-start. Produce **differentiation tiers** (reuse DifferentiationGuide). **Methodology-aware structure** (Gagné + required components around the chosen methodology).
- **Smart retry:** error-field-aware + StructuredOutput middleware + model-fallback (reroute) + escalate (no temperature-only).
- **Feedback-memory:** teacher edits at the blueprint gate (structured diff) + quality/effectiveness signals → per-teacher lesson-template/preference (soft prior into the staged reasoning), always gated.
- **Cold-plan vs expand-from-seed:** one engine, two modes — cold = full backward-design; expand-seed (unit session, topic-decomposition/008) = phases 3–5 with objectives/KCs/bloom/duration fixed + drift-guard. Default `generate→lesson_critic→revise`; `rigorous` policy = candidate-N-select.

## Acceptance criteria

- [ ] Planner runs staged backward-design (assessment-first) as focused sub-steps, not one mega-prompt; output is a valid `LessonPlan`.
- [ ] Grounding consumed; single-lesson validator + lesson_critic gate the output with bounded self-repair.
- [ ] Planner consumes 3 sources (persona/KG/mastery), calibrates accordingly, degrades on cold-start, and emits differentiation tiers + methodology-aware structure.
- [ ] Smart retry (field-aware + StructuredOutput + model-fallback + escalate); feedback-memory soft-priors from teacher edits + outcomes.
- [ ] One engine serves cold-plan and expand-from-seed (drift-guarded); rigorous policy enables candidate-select.

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_planner_staged.py`: output covers ≥2 Bloom, assessment↔objective alignment, prerequisite ordering; a violation triggers self-repair.
- [ ] `test_planner_adaptive.py`: weak-prereq persona vs advanced persona over the same topic yield different reteach/difficulty; cold-start falls back to grounding.
- [ ] `test_planner_seed_mode.py`: expand-from-seed keeps seed objectives/KCs/duration (drift-guard); cold mode runs all phases.
- [ ] `test_planner_retry.py`: a malformed field triggers field-aware repair then model-fallback then escalate.
- [ ] Run `uv run pytest -m real_llm packages/agents/tests/test_planner_*.py -v`.

## Blocked by

- .scratch/technical-debt/002-middleware-wiring-and-runner.md
- .scratch/topic-decomposition/003-sequence-consistency-validator.md
- .scratch/topic-decomposition/005-curriculum-grounding-source.md
