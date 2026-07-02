---
title: Renderer core kernel with fixture plugin
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Build the minimal production-shaped renderer kernel with a single fixture plugin that proves the full path: `render({ kind, input, context })` validates input, resolves a plugin, adapts data, renders an Eta template, sanitizes output, enforces standalone asset policy, and returns HTML with manifest, diagnostics, and metrics.

This is the tracer bullet for the rewrite. It should not migrate real artifacts yet.

## Acceptance criteria

- [ ] Public `render()` and `renderBatch()` APIs exist with `RenderRequest`, `RenderResponse`, `RenderContext`, and `RenderManifest` types.
- [ ] Plugin registry supports registration, duplicate-kind rejection, unknown-kind errors, metadata inspection, and typed `RendererError` outputs.
- [ ] A fixture plugin renders standalone HTML end-to-end and returns manifest, diagnostics, and metrics.
- [ ] Runtime schema validation is required before adapter execution.
- [ ] Unit tests cover success, validation failure, unknown kind, unsupported audience, and fixture manifest creation.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
