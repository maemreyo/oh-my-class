---
title: Active Recall mode UI polish
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish `active_recall` so retrieval practice feels intentional, structured, and teacher-visible. The gate requires `active_recall_prompt`, which exists, so this slice focuses on preview, interaction states, and recall-specific feedback.

## Acceptance criteria

- [ ] Teacher inspector explains retrieval-practice intent and required `active_recall_prompt` component.
- [ ] Student preview supports prompt, hidden/reveal answer area, confidence check, and reflection note.
- [ ] Reduced-motion users receive instant reveals rather than animated transitions.
- [ ] Print mode shows prompts first and answer key/teacher rationale separately.
- [ ] The UI distinguishes recall prompts from ordinary quiz questions.

## Detailed test suite

- [ ] Renderer test: Given active-recall prompts, when rendered, then prompt, reveal area, confidence check, and reflection note are present.
- [ ] Reduced-motion test: Given `prefers-reduced-motion`, when reveal is triggered, then no animated transition classes are required for content visibility.
- [ ] Teacher-only test: Answer/rationale appears only in teacher-only output or gated reveal, not in initial student-facing print.
- [ ] UI inspector test: Given `active_recall`, when rendered, then required component satisfaction and retrieval-practice explanation are visible.
- [ ] Accessibility test: Reveal controls are buttons with labels and work via keyboard.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
