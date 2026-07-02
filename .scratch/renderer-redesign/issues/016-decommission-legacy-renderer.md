---
title: Decommission legacy renderer paths after registry migration
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Delete obsolete renderer paths and verify no code path can bypass the plugin registry, unified sanitizer, asset policy, or public API boundary.

## Acceptance criteria

- [ ] `renderArtifactSync()` and regex-based `sanitizer.ts` are removed.
- [ ] Public semantic-anchor and inverse-thinking wrapper exports are removed.
- [ ] Old Artifact UI renderer API is removed or made internal only if still needed by plugins.
- [ ] No production caller deep-imports renderer internals.
- [ ] No `default -> lessonData()` fallback or equivalent silent routing remains.
- [ ] Full renderer test suite, TypeScript build, and quality gates pass.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 015-quality-gates-ci.md
