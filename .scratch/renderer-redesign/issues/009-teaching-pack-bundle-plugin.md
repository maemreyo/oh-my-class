---
title: Implement teaching_pack as a bundle plugin
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Implement `teaching_pack` as a bundle plugin that renders child artifacts through the registry instead of pretending to be a lesson. The bundle output must preserve child manifests and provide a bundle-level manifest.

## Acceptance criteria

- [ ] `teaching_pack` plugin validates bundle input and rejects malformed child artifacts.
- [ ] Child artifacts render through `renderBatch()` or an equivalent internal registry call.
- [ ] Bundle response includes child manifests and a bundle manifest.
- [ ] Partial failure behavior is explicit and tested.
- [ ] `teaching_pack` no longer falls through to lesson rendering.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 005-practice-plugins.md
- 006-summary-visual-plugins.md
- 007-lesson-answer-key-plugins.md
- 008-missing-contract-plugins.md
