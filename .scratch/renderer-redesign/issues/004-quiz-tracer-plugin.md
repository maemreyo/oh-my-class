---
title: Migrate quiz as the first real Artifact-Kind plugin
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `quiz` into a self-contained plugin that uses runtime schema validation, the unified theme resolver, sanitizer chokepoint, standalone asset policy, message catalog, manifest generation, and representative snapshots. This establishes the regular artifact plugin pattern.

## Acceptance criteria

- [ ] `quiz` plugin declares kind, version, schema, capabilities, sanitizer policy, adapter, and template path.
- [ ] Rendering `kind: "quiz"` produces standalone HTML with manifest, diagnostics, and metrics.
- [ ] Student output passes leak-prevention checks for answer and explanation fields where applicable.
- [ ] Golden snapshots cover preview/export/print where supported.
- [ ] Existing quiz renderer callers are either migrated or explicitly blocked until the public API migration issue.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 001-core-renderer-kernel.md
- 003-theme-sanitizer-asset-policy.md
