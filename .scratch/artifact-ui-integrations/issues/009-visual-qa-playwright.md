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

### paper-dossier (3 pages × 3 widths = 9 screenshots)
- `lesson.html` at 375/768/1280
- `answer-key.html` at 375/768/1280 (default state)
- `answer-key.html` at 375/768/1280 (revealed state — all answers expanded)
- `root-cause-session.html` at 375/768/1280 (default state)
- `root-cause-session.html` at 375/768/1280 (revealed state — checkpoints expanded)

### transit-route (1 page × 3 widths = 3 screenshots)
- `video-route.html` at 375/768/1280

### investigation-folder (1 page × 3 widths = 3 screenshots)
- `inverse-thinking.html` at 375/768/1280

### Interactivity state screenshots (5 targeted)
- `answer-key-mode-toggle-768.png` — bulk reveal/hide action
- `answer-key-jumpbox-landed-768.png` — jump-to-target landing
- `answer-key-qgrid-jump-768.png` — question grid shortcut
- `root-cause-session-revealed-768.png` — generalization checkpoint revealed
- `exam-key-qgrid-jump-768.png` — question grid shortcut

**Total: 32 screenshots** (24 default + 5 interactivity states + 3 reveal states)

## Acceptance criteria

- [ ] All 32 screenshots captured and saved to `packages/renderer/__tests__/artifact-ui/qa/screenshots/`
- [ ] Screenshots are named: `{family}-{kind}-{audience}-{state}-{width}px.png`
- [ ] No horizontal scroll at any width (content fits viewport)
- [ ] No text clipping or overflow at 375px
- [ ] Sidebar collapses to stacked layout at 768px (paper-dossier)
- [ ] Ticket card stacks vertically at 600px (navy-ticket)
- [ ] Print button is visible at 1280px, hidden in print preview
- [ ] All screenshots show `oh-my-class` brand string
- [ ] All screenshots show correct `data-artifact-theme` visual identity
- [ ] Interactivity state screenshots show correct reveal/toggle/jump behavior
- [ ] Reduced-motion screenshots show `.art-flash` removed but `.art-jump-highlight` preserved

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: Playwright test captures screenshots at all 3 widths for all pages
- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: captures interactivity state screenshots (reveal, mode-toggle, jumpbox)
- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: asserts no horizontal scroll (`document.body.scrollWidth <= viewport.width`)
- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: asserts brand string visible in viewport
- [ ] `packages/renderer/__tests__/artifact-ui/visual-qa.spec.ts`: asserts reduced-motion behavior (no `.art-flash`, `.art-jump-highlight` preserved)

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=visual-qa` → all tests pass
- Manual: open each screenshot, verify layout is correct at each width
- Manual: compare with reference screenshots from `.scratch/artifact-ui-integrations/resources/artifact-ui/qa/screenshots/`

## Blocked by

- `007-public-api-render-artifact-ui.md` — must be able to render pages for screenshots
- `008-full-tdd-test-suite.md` — tests must pass before visual QA
