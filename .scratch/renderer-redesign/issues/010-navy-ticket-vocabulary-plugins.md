---
title: Migrate navy-ticket semantic-anchor vocabulary plugins
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate semantic-anchor vocabulary rendering to `navy-ticket.teaching` and `navy-ticket.practice` plugins. Vocabulary batch export should call `render()` or `renderBatch()` rather than semantic-anchor wrapper functions.

## Acceptance criteria

- [ ] `navy-ticket.teaching` and `navy-ticket.practice` plugins validate semantic-anchor inputs and declare audience policies.
- [ ] Teacher and student projections render through the new registry API.
- [ ] Vocabulary batch exporter uses `renderBatch()` and receives manifests for all four projections.
- [ ] Public semantic-anchor wrapper exports are no longer required by production callers.
- [ ] Golden snapshots cover teaching/practice and teacher/student variants.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
