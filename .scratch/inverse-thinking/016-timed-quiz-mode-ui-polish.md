---
title: Timed Quiz mode UI polish and time badge implementation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish `timed_quiz` and implement the time-badge surface implied by the methodology gate comments. This mode should make timing visible and pedagogically useful without creating inaccessible or stressful UI.

## Acceptance criteria

- [ ] Teacher mode picker exposes Timed Quiz with duration/intensity controls and an explanation of timing purpose.
- [ ] Renderer supports time badges or equivalent timing metadata on quiz/drill items.
- [ ] Student-facing UI communicates suggested time without requiring live JavaScript timers for print/offline use.
- [ ] If interactive timer behavior exists in preview, it supports pause/restart and reduced-motion/accessibility expectations.
- [ ] Quality inspector shows whether timing metadata exists for timed items.

## Detailed test suite

- [ ] Renderer test: Given timed quiz metadata, when rendered, then each timed item shows a time badge and print-safe timing copy.
- [ ] Standalone test: Rendered timed quiz HTML has no external timer script and works offline.
- [ ] UI control test: Given Timed Quiz mode, when duration/intensity changes, then preview metadata updates and invalid durations are rejected.
- [ ] Accessibility test: Timer/badge copy is text-readable, keyboard reachable if interactive, and does not rely on motion/color alone.
- [ ] Reduced-motion test: Interactive timer preview avoids motion-heavy urgency effects when `prefers-reduced-motion` is active.
- [ ] Quality inspector test: Given missing timing metadata, when timed quiz mode is selected, then the inspector shows a warning with a field jump link.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
