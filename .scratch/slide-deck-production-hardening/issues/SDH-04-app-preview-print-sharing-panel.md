---
title: App preview Print & sharing panel for slide decks
status: ready-for-agent
labels: [ready-for-agent, slide-deck, frontend]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries

## What to build

Make the teacher dashboard preview align with the production surface model. The main slide canvas should default to a presentation view, while teacher-only notes, quality metadata, and print/share settings live in side or collapsible panels. Add a `Print & sharing` panel that lets teachers inspect student, presentation, teacher, and print surfaces and choose print layout, slides per page, and chrome behavior before export.

The slice should integrate with existing teaching-pack preview/export behavior rather than creating a parallel slide-deck workflow. It should be user-centric and avoid cluttering the main preview with every advanced option.

## Acceptance criteria

- [ ] Slide-deck app preview defaults to a clean presentation canvas, not a teacher-notes canvas.
- [ ] Teacher-only notes/metadata appear outside the slide canvas and are never mixed into the student/presentation slide DOM.
- [ ] A collapsible `Print & sharing` or equivalent panel exposes surface, print layout, slides-per-page, and chrome options with sensible defaults.
- [ ] Changing options updates preview/export requests through the typed display-preference seam rather than ad-hoc query strings.
- [ ] The UI clearly distinguishes student-safe, presentation, teacher, and print views so teachers know what students will see.
- [ ] Mobile/tablet/desktop layouts remain readable and no preview control causes horizontal overflow.
- [ ] Technical UI guards or component tests cover option state and request mapping where feasible.
- [ ] Real-LLM acceptance in SDH-07 verifies the app/gateway/export behavior if this slice touches exported output.

## Blocked by

- SDH-01-display-preferences-and-surface-contract.md
- SDH-02-safe-projections-and-chrome-policy.md
