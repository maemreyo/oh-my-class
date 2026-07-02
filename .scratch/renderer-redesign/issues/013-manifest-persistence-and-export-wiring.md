---
title: Persist rendered HTML with manifest and wire exports
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Wire renderer responses into gateway/export persistence so final HTML and `RenderManifest` are stored together. Exports should use persisted final HTML by default and only re-render explicitly when requested.

## Acceptance criteria

- [ ] Gateway render flow stores `rendered_html` and `RenderManifest` together.
- [ ] Manifest includes renderer, plugin, template, theme, sanitizer policy versions, render mode, locale, audience, requestId, renderedAt, and contentHash.
- [ ] Export writer uses persisted rendered HTML when available.
- [ ] Explicit re-render creates a new manifest rather than mutating old output silently.
- [ ] Tests cover manifest persistence and export behavior for at least one single artifact and one teaching pack bundle.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 002-worker-protocol-v2.md
- 009-teaching-pack-bundle-plugin.md
