---
title: Add renderer i18n catalog, print mode, and visual QA smoke
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Add centralized renderer UI messages for Vietnamese and English, make print mode first-class, and add visual/print smoke tests for representative regular and Artifact UI plugins.

## Acceptance criteria

- [ ] `MessageCatalog` resolves renderer chrome labels by locale and fails tests for missing keys.
- [ ] Templates use message keys for renderer chrome instead of hard-coded labels.
- [ ] `renderMode: "print"` is supported by printable plugins or rejected with a typed unsupported-mode error.
- [ ] Visual smoke covers representative regular and Artifact UI plugins.
- [ ] Print smoke covers quiz, worksheet, lesson, and answer-key-like output.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 005-practice-plugins.md
- 007-lesson-answer-key-plugins.md
- 011-artifact-ui-specialty-plugins.md
