---
title: Migrate worksheet and drill plugins end-to-end
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `worksheet` and `drill` into plugins that follow the quiz tracer pattern and prove printable practice artifacts through the new registry API.

## Acceptance criteria

- [ ] `worksheet` and `drill` plugins declare complete plugin metadata and runtime schemas.
- [ ] Both plugins render through `render()` with standalone output and manifests.
- [ ] Print mode is supported or explicitly rejected with `UNSUPPORTED_RENDER_MODE`/equivalent typed error.
- [ ] Student leak-prevention tests cover question answers, explanations, and teacher-only fields.
- [ ] Golden snapshots cover representative worksheet and drill inputs.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
