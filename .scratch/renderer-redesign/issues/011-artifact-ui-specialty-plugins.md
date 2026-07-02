---
title: Migrate specialty Artifact UI plugins
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate remaining Artifact UI render paths to plugins: `investigation-folder.inverse-thinking`, `paper-dossier.root-cause-session`, and `transit-route.video-route`. Managed inline interactivity must be declared by plugin policy.

## Acceptance criteria

- [ ] All three plugins declare complete metadata, schemas, capabilities, sanitizer policies, adapters, and templates.
- [ ] Inverse-thinking callers use `render()` instead of `renderInverseThinkingHtml`.
- [ ] Root-cause session and video route render through the registry with standalone output and manifests.
- [ ] Managed inline JS is allowed only for plugins that declare `{ id, sourcePath, sha256 }`; hash mismatch or undeclared inline script fails asset policy.
- [ ] Golden snapshots and visual smoke cover representative outputs.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 007-lesson-answer-key-plugins.md
- 010-navy-ticket-vocabulary-plugins.md
