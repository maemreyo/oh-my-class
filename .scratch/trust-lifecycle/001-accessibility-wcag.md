---
title: Accessibility (WCAG 2.1 AA) for artifacts and dashboard
status: done
labels: []
created: 2026-06-30
---

## What to build

Make generated artifacts and the teacher dashboard accessible (WCAG 2.1 AA) — critical for K-12 inclusion and often legally required. Infographics already carry contrast/alt-text; generalize to all artifacts.

- **axe-core** assertions in (a) renderer tests per artifact type (deterministic) and (b) dashboard Playwright e2e (reuse the 4-width setup).
- **Critical a11y violations become hard-blocks** (extend the existing `HARD_BLOCKS`): contrast below AA, missing alt, broken heading order, missing form labels, missing `lang`. Fail-closed like answer-key-leakage — offline (no external assets).
- **K-12 inclusion**: every artifact carries alt/aria + `longDescription` for diagrams/SVG (generalize the infographic pattern); enforce reading-level by age-band (reuse `readability_checker`); provide a **high-contrast / dyslexia-friendly theme variant** (theme system supports variants in `common/branding/kits/`).

## Acceptance criteria

- [x] Generated artifacts and the dashboard pass axe-core at WCAG 2.1 AA; critical violations are hard-blocks (fail-closed).
- [x] All artifact types carry alt/aria; diagrams/SVG have `longDescription`.
- [x] Reading-level is enforced per age-band.
- [x] A high-contrast/dyslexia-friendly theme variant exists and renders offline (no external assets).

## Detailed test suite

- [x] `packages/renderer/__tests__/a11y-artifacts.test.ts`: each artifact type carries WCAG-critical metadata; injected contrast/alt/heading/lang/form-label/long-description violations are caught as Layer 3 hard-blocks in `packages/quality/tests/test_layer3_accessibility.py`.
- [x] `apps/web/tests/e2e/a11y-dashboard.spec.ts` (Playwright + axe) at 375/768/1280/1920: dashboard passes AA.
- [x] `apps/web/tests/e2e/a11y-artifacts.spec.ts` (Playwright + axe) at 375/768/1280/1920: rendered lesson/worksheet/quiz/drill/recap/infographic pass AA.
- [x] Theme variant test: high-contrast/dyslexia theme renders standalone with no external assets.
- [x] Run focused renderer, quality, web typecheck, and Playwright E2E gates.

## Verification

- `uv run pytest packages/quality/tests/test_layer3_accessibility.py packages/quality/tests/test_layer3_html.py packages/quality/tests/test_age_band.py -q` → 71 passed.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/a11y-artifacts.test.ts __tests__/theme.test.ts __tests__/standard-artifact-matrix.test.ts` → 47 passed.
- `pnpm --filter @oh-my-class/web typecheck` → passed.
- `pnpm --filter @oh-my-class/web exec playwright test tests/e2e/a11y-dashboard.spec.ts --reporter=line` → 4 passed across 375/768/1280/1920.
- `pnpm --filter @oh-my-class/web exec playwright test tests/e2e/a11y-artifacts.spec.ts` → 24 passed across 6 artifact types × 4 widths.
- `pnpm --filter @oh-my-class/renderer build` → passed.
- LSP diagnostics clean for changed Python/TypeScript/HTML test and source files.

## Blocked by

None - can start immediately
