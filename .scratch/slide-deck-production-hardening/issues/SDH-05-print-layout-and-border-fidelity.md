---
title: Slide deck print layout and crisp border fidelity
status: ready-for-agent
labels: [ready-for-agent, slide-deck, frontend]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries

## What to build

Implement production print behavior for slide-deck exports. Print must be a separate projection that shows the full deck, not only the active presentation slide. It should support paged grid mode with `1`, `2`, `4`, or `6` slides per page and continuous mode for vertical handouts. Slides should preserve a 16:9 aspect boundary using real layout sizing, not transform scaling.

Fix the blurry/faded corner-border problem as a rendering-correctness issue. Print mode should use a single border owner per slide card, solid crisp borders, deterministic radius, and no transform/shadow/filter effects that blur corners or text. Screen mode may keep subtle polish, but print must optimize readability and fidelity.

## Acceptance criteria

- [ ] Print media shows every slide in the deck regardless of which slide is active on screen.
- [ ] Paged grid supports `1`, `2`, `4`, and `6` slides per page and continuous mode ignores slides-per-page cleanly.
- [ ] Printed slide cards preserve a 16:9 aspect ratio without transform-based scaling.
- [ ] Print controls/navigation are hidden in print output.
- [ ] Print borders and rounded corners render crisply by using solid borders, no print shadows/filters/transforms, and a single border owner.
- [ ] Mobile screen layout remains readable and independent from print layout.
- [ ] Browser QA captures or records presentation, mobile, and print-media evidence for the actual rendered deck.
- [ ] SDH-07 later proves the same print behavior on real-LLM actual exported HTML.

## Blocked by

- SDH-01-display-preferences-and-surface-contract.md
- SDH-03-standalone-presentation-print-controls.md
