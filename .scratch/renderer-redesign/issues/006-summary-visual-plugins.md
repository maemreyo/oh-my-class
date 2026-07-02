---
title: Migrate recap and infographic plugins end-to-end
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `recap` and `infographic` into registry plugins to prove non-question artifacts and visual-heavy artifacts under the new renderer kernel.

## Acceptance criteria

- [ ] `recap` and `infographic` plugins declare complete plugin metadata and runtime schemas.
- [ ] Both plugins render through `render()` with standalone output and manifests.
- [ ] Infographic output preserves safe inline visual content while passing asset policy.
- [ ] Golden snapshots cover representative recap and infographic inputs.
- [ ] Visual smoke coverage exists for infographic output.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
