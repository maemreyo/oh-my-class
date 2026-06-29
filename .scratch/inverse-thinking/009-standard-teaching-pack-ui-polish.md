---
title: Standard teaching pack UI polish and preview baseline
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish the standard teaching-pack experience so it becomes the baseline every special methodology mode must match or intentionally exceed. This slice covers the ordinary lesson/worksheet/quiz/drill/recap/infographic surfaces, teacher gate preview, theme selection, and export-readiness affordances.

This should not add inverse-thinking or other special-mode semantics. It creates the high-quality default experience and shared UI expectations.

## Acceptance criteria

- [ ] Standard artifact previews for lesson, worksheet, quiz, drill, recap, and infographic are visually coherent across default, ocean, and forest themes.
- [ ] Teacher Gate 1 and Teacher Gate 2 preview states show artifact completeness, quality status, export readiness, and next actions in a clear hierarchy.
- [ ] Export format requirements are visible before export: HTML needs lesson content, GIFT needs quiz content, and unsupported combinations are disabled with explanations.
- [ ] Print and mobile preview controls are available from the shared preview shell.
- [ ] Empty, loading, quality-failed, repair-in-progress, teacher-rejected, and export-ready states all have distinct UI copy and actions.
- [ ] Existing standalone HTML invariants remain unchanged: no external assets, brand string present, answer keys separated.

## Detailed test suite

- [ ] Renderer matrix tests: For each standard artifact type × each theme, render HTML and assert DOCTYPE, viewport meta, `oh-my-class`, no `http://` or `https://` asset references, print styles, and no answer-key leakage.
- [ ] `apps/web` component tests: Given each gate state, when the standard preview renders, then the correct primary action, secondary action, and explanatory copy are visible.
- [ ] Export chooser tests: Given selected artifact types, when export formats are toggled, then invalid format/artifact combinations are disabled with accessible explanations.
- [ ] Responsive visual tests: Capture standard preview at 375/768/1280/1920px for at least lesson and quiz artifacts.
- [ ] Accessibility tests: Gate actions are keyboard reachable, preview tabs have correct roles, and status updates announce through `aria-live`.
- [ ] Regression tests: Existing renderer tests for template-library/theme/render contracts still pass after UI polish.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
