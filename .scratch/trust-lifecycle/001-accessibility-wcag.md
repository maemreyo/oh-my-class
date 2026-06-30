---
title: Accessibility (WCAG 2.1 AA) for artifacts and dashboard
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make generated artifacts and the teacher dashboard accessible (WCAG 2.1 AA) — critical for K-12 inclusion and often legally required. Infographics already carry contrast/alt-text; generalize to all artifacts.

- **axe-core** assertions in (a) renderer tests per artifact type (deterministic) and (b) dashboard Playwright e2e (reuse the 4-width setup).
- **Critical a11y violations become hard-blocks** (extend the existing `HARD_BLOCKS`): contrast below AA, missing alt, broken heading order, missing form labels, missing `lang`. Fail-closed like answer-key-leakage — offline (no external assets).
- **K-12 inclusion**: every artifact carries alt/aria + `longDescription` for diagrams/SVG (generalize the infographic pattern); enforce reading-level by age-band (reuse `readability_checker`); provide a **high-contrast / dyslexia-friendly theme variant** (theme system supports variants in `common/branding/kits/`).

## Acceptance criteria

- [ ] Generated artifacts and the dashboard pass axe-core at WCAG 2.1 AA; critical violations are hard-blocks (fail-closed).
- [ ] All artifact types carry alt/aria; diagrams/SVG have `longDescription`.
- [ ] Reading-level is enforced per age-band.
- [ ] A high-contrast/dyslexia-friendly theme variant exists and renders offline (no external assets).

## Detailed test suite

- [ ] `packages/renderer/__tests__/a11y-artifacts.test.ts`: each artifact type passes axe-core; an injected contrast/alt/heading violation is caught (hard-block).
- [ ] `apps/web/tests/a11y-dashboard.spec.ts` (Playwright + axe) at 375/768/1280/1920: dashboard passes AA.
- [ ] Theme variant test: high-contrast/dyslexia theme renders standalone with no external assets.
- [ ] Run `pnpm -F @oh-my-class/renderer test` and `pnpm -F web test:e2e`.

## Blocked by

None - can start immediately
