---
title: Inverse Thinking methodology package and projections
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Create the pure methodology domain module for inverse thinking. One canonical `InverseThinkingPack` should normalize and project into consistent lesson, worksheet, quiz, and drill outputs without regenerating pedagogy independently for each artifact.

This slice proves the core SoC boundary: methodology logic lives outside the renderer and gateway, and projections are pure/testable functions that downstream layers can consume.

## Acceptance criteria

- [ ] A `packages/methodologies/inverse_thinking` module exists with pure functions for normalize, semantic validation, and projection.
- [ ] The module does not import from `services/*` or `apps/*`.
- [ ] Lesson projection includes the full disaster-first case flow and synthesis/summary information.
- [ ] Worksheet projection includes evidence cards, clue work, safe-zone prompts, and summary-table practice.
- [ ] Quiz/drill projections derive clue/disaster-based assessment items from the same canonical cases.
- [ ] Teacher-only data remains separated from student-facing projections.
- [ ] Projection tests prove lesson, worksheet, quiz, and drill are internally consistent with the same canonical pack.
- [ ] Projection tests cover English, math, and science fixtures.

## Detailed test suite

- [ ] `packages/methodologies/inverse_thinking/tests/test_normalize.py`: Given minimally valid packs, when normalized, then IDs, ordering, default frame hints, and teacher-only containers are deterministic.
- [ ] `packages/methodologies/inverse_thinking/tests/test_semantic_validation.py`: Given rule-first, clue-less, boundary-less, and synthesis-less packs, when validated, then failures name the exact case and semantic step.
- [ ] `packages/methodologies/inverse_thinking/tests/test_project_lesson.py`: Given one canonical pack, when projected to lesson, then the output includes disaster-first cases, clues, safe zones, filing notes, and summary rows in order.
- [ ] `packages/methodologies/inverse_thinking/tests/test_project_worksheet.py`: Given the same pack, when projected to worksheet, then evidence cards and clue/safe-zone prompts match the canonical case IDs.
- [ ] `packages/methodologies/inverse_thinking/tests/test_project_quiz_drill.py`: Given the same pack, when projected to quiz and drill, then assessment items reuse canonical clues/boundaries without contradicting the lesson projection.
- [ ] `packages/methodologies/inverse_thinking/tests/test_teacher_only_separation.py`: Given teacher rationales, when any student projection is produced, then no teacher-only answer/rationale appears in student components.
- [ ] Import-boundary check: run `lint-imports` and verify the methodology package imports `common/contracts` only, never `services/*` or `apps/*`.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
