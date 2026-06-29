---
title: Contrastive Pairs mode UI polish
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish `contrastive_pairs` so teachers and students can clearly compare two easily confused concepts, examples, or language patterns. A renderer template already exists; this issue focuses on teacher-facing mode UI, responsive presentation, and quality visibility.

## Acceptance criteria

- [ ] Teacher mode inspector explains what pair is being contrasted and why the contrast matters.
- [ ] Preview UI makes the two sides visually balanced, with shared criteria and explicit difference markers.
- [ ] Renderer handles long Vietnamese and English examples without overflow.
- [ ] Student-facing output distinguishes examples, non-examples, and boundary notes.
- [ ] Teacher-only explanations remain separated from student-facing cards.

## Detailed test suite

- [ ] Renderer test: Given a contrastive-pair component with long labels and examples, when rendered, then both sides remain visible at mobile and desktop widths.
- [ ] Renderer test: Given teacher-only rationales, when student HTML renders, then rationales are absent from student-facing DOM.
- [ ] UI inspector test: Given `contrastive_pairs`, when the inspector opens, then it shows pair title, side labels, and required component satisfaction.
- [ ] Visual QA: Capture side-by-side desktop and stacked mobile layouts; verify clear hierarchy and no text clipping.
- [ ] Accessibility test: Pair sides are navigable with headings/regions and do not rely on color alone to indicate differences.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
