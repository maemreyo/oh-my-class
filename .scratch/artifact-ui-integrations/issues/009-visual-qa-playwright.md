---
title: Visual QA — Playwright screenshots at 375/768/1280 for all families
status: ready-for-agent
labels: [renderer, qa, visual, playwright]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Visual QA using Playwright to capture screenshots of all rendered artifact UI output at 375px (mobile), 768px (tablet), and 1280px (desktop) widths. This catches responsive layout bugs that code review misses (as proven by the core-primitives mobile overflow bug found in the resources' QA pass).

## Screenshot inventory

### navy-ticket (4 pages × 3 widths = 12 screenshots)
- `teaching.teacher.html` at 375/768/1280
- `teaching.student.html` at 375/768/1280
- `practice.teacher.html` at 375/768/1280
- `practice.student.html` at 375/768/1280

### paper-dossier (2 pages × 3 widths = 6 screenshots)
- `lesson.html` at 375/768/1280
- `answer-key.html` at 375/768/1280

### transit-route (1 page × 3 widths = 3 screenshots)
- `video-route.html` at 375/768/1280

### investigation-folder (1 page × 3 widths = 3 screenshots)
- `inverse-thinking.html` at 375/768/1280

**Total: 24 screenshots**

## Acceptance criteria

- [ ] All 24 screenshots captured and saved to `packages/renderer/__tests__/artifact-ui/qa/screenshots/`
- [ ] Screenshots are named: `{family}-{kind}-{audience}-{width}px.png`
- [ ] No horizontal scroll at any width (content fits viewport)
- [ ] No text clipping or overflow at 375px
- [ ] Sidebar collapses to stacked layout at 768px (paper-dossier)
- [ ] Ticket card stacks vertically at 600px (navy-ticket)
- [ ] Print button is visible at 1280px, hidden in print preview
- [ ] All screenshots show `oh-my-class` brand string
- [ ] All screenshots show correct `data-artifact-theme` visual identity

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: Playwright test captures screenshots at all 3 widths for all 8 pages
- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: asserts no horizontal scroll (`document.body.scrollWidth <= viewport.width`)
- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: asserts brand string visible in viewport

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=visual-qa` → all tests pass
- Manual: open each screenshot, verify layout is correct at each width
- Manual: compare with reference screenshots from `.scratch/artifact-ui-integrations/resources/artifact-ui/qa/screenshots/`

## Blocked by

- `007-public-api-render-artifact-ui.md` — must be able to render pages for screenshots
- `008-full-tdd-test-suite.md` — tests must pass before visual QA
