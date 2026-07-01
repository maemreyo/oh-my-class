---
title: Redesign semantic vocabulary artifacts with the Artifact UI layer
status: ready-for-agent
labels: []
created: 2026-07-01
---

## Parent

ADR-023: Artifact UI Layer from Template Corpus

## What to build

Apply the Artifact UI layer to vocabulary-batch semantic-anchor projections. The goal is for `SemanticAnchorCluster` and `PracticeSet` outputs to feel like the `neo-tu-duy-template.html` design language: expressive hero, navy/paper ticket atmosphere, tactile ticket cards, mono labels, semantic chains, contrast quotes, and teacher-only delivery panels.

The redesign must preserve the existing contract-first model and projection safety. Student files must remain separate from teacher files and must not contain teacher scripts, source notes, answer keys, rationales, or hidden teacher-only DOM.

## Acceptance criteria

- [ ] Vocabulary teaching teacher/student projections use Artifact UI primitives instead of generic dashboard-style HTML.
- [ ] Vocabulary practice teacher/student projections use the same family language and clearly separate prompt, answer, rationale, and student-safe fields.
- [ ] Passed clusters export teacher HTML, student HTML, GIFT, and H5P as before.
- [ ] Needs-review clusters export teacher review files only; student and LMS files stay withheld until approval.
- [ ] Failed clusters export diagnostics-only output with the Artifact UI diagnostics primitive.
- [ ] Tests prove student HTML does not contain teacher scripts, source notes, answer keys, rationales, or teacher-only DOM markers.
- [ ] Export package tests prove `index.html`, manifest links, per-cluster folders, GIFT, and H5P still work.
- [ ] Browser QA covers generated vocabulary artifacts at 375px, 768px, and 1280px, including print preview or print CSS inspection.

## Blocked by

- `.scratch/artifact-ui-layer/001-core-artifact-design-system.md`
