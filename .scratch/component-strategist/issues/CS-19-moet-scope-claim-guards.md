---
title: Add scope and claim guards for non-public MOET mode
status: ready-for-agent
labels: [component-strategist, vietnamese, release-gate]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Prevent hidden/internal Vietnamese improvements from being presented as public MOET-compliant generation. When the MOET extraction and QA pass has not been completed for the relevant grade/subject scope, UI, export, docs, and release-gate messaging must not claim “đúng chương trình VN/MOET”.

This slice guards scope and copy; it does not implement the full Vietnamese curriculum extraction.

## Acceptance criteria

- [ ] Internal/pre-user Vietnamese strategist output is not labeled as public MOET-compliant.
- [ ] UI/export-facing copy can distinguish internal Vietnamese improvement from verified MOET-compliant launch scope.
- [ ] Release gate checks fail if public copy claims MOET compliance before the scoped extraction and QA pass is complete.
- [ ] Existing English/non-MOET flows are not blocked by the MOET claim guard.
- [ ] Tests cover no-claim leakage in representative UI/export/release-gate surfaces.

## Blocked by

- CS-07 blueprint approval strategy UX.
- CS-14 hidden/internal rollout controls.
