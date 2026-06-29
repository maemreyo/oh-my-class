---
title: Add Inverse Thinking teacher controls and structured editor
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add user-centric teacher controls for inverse thinking using progressive disclosure. Teachers should be able to choose the method, optionally override creative direction, edit structured case fields, preview the rendered artifact, and inspect the teaching rationale without editing raw HTML.

This slice should use generated schemas from the canonical contracts and should remain compatible with existing dashboard flows.

## Acceptance criteria

- [ ] Teacher creation/edit flow exposes `Teaching approach`: Auto, Standard, and Inverse Thinking.
- [ ] Selecting Inverse Thinking reveals optional controls for creative direction, intensity, and student output.
- [ ] Creative direction supports Auto, Detective Case, Courtroom Trial, Mythbusters Lab, Survival Guide, Disaster Report, and Custom via registry-driven IDs.
- [ ] Structured editor supports field-level edits for foil, disaster, key clues, safe zone, filing note, and student task.
- [ ] Teacher can request scoped regeneration for a field or case without regenerating the entire pack.
- [ ] Preview shows the rendered artifact as students/print/export will see it.
- [ ] A collapsible methodology inspector explains selected frame, disaster-first flow, clues, safe-zone boundary, student task, and quality warnings.
- [ ] UI tests cover selecting inverse thinking, overriding creative direction, editing a structured field, and seeing preview/inspector updates.

## Detailed test suite

- [ ] `apps/web` component tests: Given the teaching approach selector, when `Inverse Thinking` is chosen, then creative direction, intensity, and student-output controls appear via progressive disclosure.
- [ ] Structured editor tests: Given an `InverseThinkingCase`, when a teacher edits `foil`, `disaster`, `key_clues`, `safe_zone`, `filing_note`, or `student_task`, then generated schema validation runs and the preview updates without raw HTML editing.
- [ ] Regeneration action tests: Given a selected field/case, when `Regenerate field` or `Regenerate case` is clicked, then only the scoped regeneration payload is submitted.
- [ ] Inspector tests: Given quality warnings, when the inspector opens, then it lists frame rationale, disaster-first sequence, key clues, safe-zone boundary, student task, and warning anchors.
- [ ] Accessibility tests: Keyboard-only navigation reaches every field, action, preview tab, and inspector section; field errors are announced with `role="alert"` or `aria-live`.
- [ ] Playwright flow: Teacher selects Inverse Thinking, overrides `detective_case`, edits one case field, previews the artifact, and approves without losing edits.
- [ ] Visual QA screenshots at 375/768/1280px for the editor, preview, and inspector states.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/002-methodology-package-and-projections.md
- .scratch/inverse-thinking/003-pipeline-wiring.md
- .scratch/inverse-thinking/004-quality-gates-and-repair.md
- .scratch/inverse-thinking/005-renderer-standalone-html.md
