---
title: Add renderer rewrite quality gates to CI
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Add the required quality gate suite for the rewritten renderer: registry completeness, golden snapshots, leak-prevention invariant, sanitizer XSS corpus, worker protocol tests, and visual/print smoke.

## Acceptance criteria

- [ ] Registry completeness fails if any of the 12 existing artifact types or required Artifact UI kinds lacks a plugin.
- [ ] Golden snapshot comparisons use the Phase 0 current-renderer baselines and cover representative `(kind, audience, renderMode)` combinations.
- [ ] Leak-prevention invariant runs against every student-capable plugin.
- [ ] XSS corpus runs against every sanitizer policy and SVG sanitizer where applicable.
- [ ] Worker protocol contract tests run in CI.
- [ ] Visual/print smoke tests run or are clearly gated for environments without browser support.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 012-i18n-print-and-visual-qa.md
- 014-public-api-boundary-and-caller-migration.md
