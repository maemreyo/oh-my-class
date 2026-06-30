---
title: unit_planner sub-agent — grounded, confidence-aware decomposition
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the sub-agent that turns a topic into a coarse `LessonSequence` using a three-stage pipeline (ADR-017): **retrieve grounding → Curricular-CoT adapt → validate**. It assigns a primary methodology per session by Bloom level, emits a confidence/grounding signal, and fails closed when ungrounded and ambiguous.

`packages/agents/sub_agents/unit_planner/` (mirrors the existing planner sub-agent layout):

- Consumes grounding (issue 005) and, **when present**, persona snapshot (issue 013) + template/teacher-preference priors (issue 014) as **soft, optional** inputs — absent priors must not block (cold-start behaves like grounded-only). This issue does **not** block on 013/014.
- Curricular-CoT (extraction → synthesis → scoring) stays **inside** `unit_planner` as staged prompting — not split into separate agents.
- Produces a thin sequence (per-session outline only — no Gagné `learning_plan`; children expand later in issue 008).
- Pipeline: `unit_planner → sequence_critic (issue 021) → bounded self-repair → SequenceConsistencyValidator (issue 003)`. HARD issues from critic/validator drive self-repair; residual issues are attached for the gate.
- Emits `confidence`, `grounding_status`, `open_questions`, `low_confidence_decisions`.
- Fail-closed: when grounding is `ungrounded` AND the topic is ambiguous, raise `CLARIFICATION_REQUIRED` (reuse the existing gate) instead of guessing.

Gate behind `features.topic_decomposition_v1`.

## Acceptance criteria

- [ ] `unit_planner` node runs retrieve → adapt → validate and outputs a schema-valid `LessonSequence`.
- [ ] Each `SessionPlan` is assigned a `methodology_primary` consistent with its Bloom level (e.g. remember→active_recall/concept_map, apply→timed_quiz, analyze→contrastive_pairs).
- [ ] HARD validator issues trigger a self-repair loop (bounded); unresolved issues are surfaced, not silently dropped.
- [ ] Output includes `confidence`, `grounding_status`, `open_questions`, `low_confidence_decisions`.
- [ ] When `ungrounded` + ambiguous, the agent raises `CLARIFICATION_REQUIRED` rather than emitting a confident sequence.
- [ ] Total duration of the produced sequence respects the grounding norms and ±10% of the requested total.
- [ ] Cold-start (no persona/template priors) produces a valid grounded sequence — priors are optional, never required.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`; real grounding source.)

- [ ] `packages/agents/tests/test_unit_planner.py`: "Phân số — Toán Lớp 5" produces a `grounded` sequence of 2–6 sessions, each ≤4 KCs, ≥2 Bloom levels across the sequence, passing `SequenceConsistencyValidator`.
- [ ] same file: every session has a `methodology_primary`; the assignment varies by Bloom level across the sequence.
- [ ] `packages/agents/tests/test_unit_planner_fail_closed.py`: a nonsense/ungrounded topic raises `CLARIFICATION_REQUIRED` and does not emit a sequence.
- [ ] `packages/agents/tests/test_unit_planner.py`: when the LLM first returns a 5-KC session, the self-repair loop produces a final sequence with ≤4 KC/session (validator passes).
- [ ] Confidence test: low-confidence structural choices appear in `low_confidence_decisions` with options + rationale.
- [ ] Run `uv run pytest packages/agents/tests/test_unit_planner*.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
- .scratch/topic-decomposition/003-sequence-consistency-validator.md
- .scratch/topic-decomposition/005-curriculum-grounding-source.md
