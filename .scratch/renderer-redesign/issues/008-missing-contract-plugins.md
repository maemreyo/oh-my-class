---
title: Add first-class plugins for previously missing contract types
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Add first-class plugins for `flashcard_deck`, `reading_passage`, `exit_ticket`, and `roadmap` so these existing contract types no longer fall through to lesson rendering or remain sanitizer-only concepts.

## Acceptance criteria

- [ ] All four plugins declare complete plugin metadata, schemas, capabilities, sanitizer policies, adapters, and templates.
- [ ] Each plugin renders through `render()` with standalone output and a manifest.
- [ ] Registry completeness tests include all four kinds.
- [ ] Golden snapshots cover representative input for each plugin.
- [ ] Print support is declared and tested for printable kinds.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
