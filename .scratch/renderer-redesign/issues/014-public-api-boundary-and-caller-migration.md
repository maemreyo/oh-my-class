---
title: Enforce renderer public API boundary and migrate callers
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Make `@oh-my-class/renderer` expose only the new public API and migrate all current production callers to `render()`/`renderBatch()`. Remove public dependency on legacy wrappers.

The actual runtime caller surface is intentionally small: TypeScript render HTML callers are primarily vocabulary batch export, while gateway rendering crosses the subprocess protocol. Treat this as a cutover issue, not a broad application rewrite.

## Acceptance criteria

- [ ] `package.json` exports block deep imports into renderer internals.
- [ ] Gateway worker, vocabulary batch exporter, inverse-thinking callers, and any quality/preview callers use the new API.
- [ ] TypeScript builds fail for deep imports outside the public surface.
- [ ] Public exports include only approved API, types, and errors.
- [ ] Legacy public functions are no longer used by production callers.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 002-worker-protocol-v2.md
- 010-navy-ticket-vocabulary-plugins.md
- 011-artifact-ui-specialty-plugins.md
- 013-manifest-persistence-and-export-wiring.md
