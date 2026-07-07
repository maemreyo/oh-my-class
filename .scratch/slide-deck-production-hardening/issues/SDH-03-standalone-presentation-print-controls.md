---
title: Standalone slide deck presentation and print controls
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries

## What to build

Upgrade the standalone slide-deck HTML so a teacher can use it offline as a restrained presentation player and still adjust print behavior without returning to the app. The standalone output should remain framework-free, CDN-free, self-contained, and student-safe by default.

V1 controls should include previous/next, keyboard navigation, progress, print button, print layout selector, slides-per-page selector, and chrome toggle only when the active surface permits it. The standalone file should support hash/query overrides plus namespaced localStorage for teacher preferences, while degrading gracefully if storage is unavailable.

## Acceptance criteria

- [ ] Standalone HTML opens in presentation-safe mode by default and contains no teacher-only data unless explicitly rendered as a teacher surface.
- [ ] Previous/next buttons, arrow-key navigation, and progress state work without external JS or frameworks.
- [ ] Print controls can select paged `1/2/4/6` and continuous modes and update the rendered print projection classes/options.
- [ ] Controls are hidden from printed output and do not appear in student-clean surfaces.
- [ ] Hash/query options can initialize the surface or print mode, and namespaced localStorage persists teacher preferences when available.
- [ ] Accessibility is classroom-ready: labeled controls, focus-visible states, reduced-motion support, no keyboard traps, no hover-only critical controls.
- [ ] Technical browser QA exercises navigation, option changes, reduced motion, mobile width, and print media on a rendered deck.
- [ ] Final acceptance for this behavior is proven by SDH-07 on actual real-LLM exported HTML.

## Blocked by

- SDH-01-display-preferences-and-surface-contract.md
- SDH-02-safe-projections-and-chrome-policy.md
