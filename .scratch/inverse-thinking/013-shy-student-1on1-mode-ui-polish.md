---
title: Shy Student 1:1 mode UI polish
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish `shy_student_1on1` around safe, low-pressure roleplay. The gate requires `roleplay_script`, which exists, so this issue focuses on teacher-facing affordances, readable roleplay output, and accessibility.

## Acceptance criteria

- [ ] Teacher mode inspector explains the 1:1/shy-student intent and required `roleplay_script` component.
- [ ] Roleplay preview clearly separates teacher line, student line, optional cue, and confidence scaffold.
- [ ] Student-facing output avoids public-performance pressure and uses supportive language.
- [ ] Print layout supports one-script-per-page or compact practice card layout.
- [ ] Teacher-only coaching notes are separated from student-facing scripts.

## Detailed test suite

- [ ] Renderer test: Given a roleplay script with teacher/student/cue/coaching fields, when rendered for students, then coaching notes are absent and role labels are clear.
- [ ] UI inspector test: Given `shy_student_1on1`, when the inspector renders, then it shows intent, required component status, and teacher-only notes status.
- [ ] Accessibility test: Role labels are announced as text, not only by color; keyboard navigation reaches script controls.
- [ ] Print test: Render multi-script output and assert page-break classes or print sections prevent split roleplay cards.
- [ ] Tone regression: Fixture text avoids shame/public-performance copy and keeps supportive phrasing.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
