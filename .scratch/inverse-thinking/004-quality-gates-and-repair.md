---
title: Add strict Inverse Thinking quality gates and repair feedback
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add inverse-thinking quality validation so generated output fails closed when it does not actually follow disaster-first pedagogy, leaks teacher-only data, or becomes generic despite being structurally valid.

The gate should distinguish critical correctness failures from repairable creativity warnings so self-healing can improve weak but salvageable output before teachers see it.

## Acceptance criteria

- [ ] Quality logic recognizes structured inverse-thinking payloads and validates them before rendered export readiness.
- [ ] Critical failures include rule-first ordering, missing disaster, vague/non-specific disaster, missing key clues, missing safe-zone boundary, incorrect misconception/foil relationship, and answer-key leakage.
- [ ] Major warnings include generic/boring disaster, weak metaphor consistency, missing signature element, over-copying the reference template, or age-inappropriate tone.
- [ ] Gate output includes actionable repair feedback scoped to the failing field or case where possible.
- [ ] The pipeline does not silently downgrade failed inverse-thinking output into a standard lesson.
- [ ] Tests cover critical fail, warning/self-repair, and pass scenarios.
- [ ] Tests use English, math, and science fixtures to prove subject-agnostic validation.

## Detailed test suite

- [ ] `packages/quality/tests/test_inverse_thinking_gate_critical.py`: Given packs with rule-first ordering, missing disaster, missing clues, missing safe zone, or missing filing note, when validated, then each produces a critical failure.
- [ ] `packages/quality/tests/test_inverse_thinking_gate_warnings.py`: Given structurally valid but generic disasters, weak metaphor consistency, missing signature elements, or over-copied template language, when validated, then each produces a major warning with repair guidance.
- [ ] `packages/quality/tests/test_inverse_thinking_gate_answer_leakage.py`: Given answer/rationale text in student-facing fields, when validated, then the gate fails critically.
- [ ] `packages/quality/tests/test_inverse_thinking_repair_feedback.py`: Given a failing case, when gate feedback is emitted, then the feedback includes case ID, field path, severity, and a scoped repair instruction.
- [ ] `tests/integration/test_inverse_thinking_no_silent_downgrade.py`: Given repeated repair failure, when the pipeline exhausts repair attempts, then it escalates/asks teacher and does not generate a standard lesson silently.
- [ ] Fixture matrix: run the gate against English grammar, math misconception, and science false-model fixtures.
- [ ] Run `uv run pytest packages/quality/tests -v` and `make calibrate` when Layer 4 judge criteria are touched.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/002-methodology-package-and-projections.md
- .scratch/inverse-thinking/003-pipeline-wiring.md
