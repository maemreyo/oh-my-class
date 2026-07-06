---
title: Add slide-native teacher preview UX inside the existing approval gate
status: ready-for-agent
labels: [slide-deck-engine, frontend, teacher-gate, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-042.

## What to build

Adapt the existing teacher approval experience so `slide_deck` remains a normal artifact in progress/status lists but opens a slide-native preview when reviewed. The preview should help teachers assess the deck as a presentation, not as one long HTML document.

The UX should include slide navigation, current slide position, optional outline/thumbnail rail where feasible, teacher notes/facilitation panel, student/teacher/print surface toggles, warnings for optional online media, and scoped feedback controls that can target deck, slide, block, or interaction.

This slice must reuse the existing teacher gate lifecycle and approval actions. It must not silently bypass compliance or create a second approval workflow.

## Acceptance criteria

- [ ] `slide_deck` appears in artifact progress/status displays with clear teacher-facing label.
- [ ] Approval preview can load student presentation, teacher guide, and print surfaces for the same slide deck snapshot.
- [ ] Teacher notes and answer guidance appear only in teacher surface/panel.
- [ ] Student surface preview does not contain teacher-only notes or answer data.
- [ ] Scoped feedback controls capture target level and stable target ID where available.
- [ ] Online media warnings are visible in teacher preview when a deck contains `requires_network` media.
- [ ] Browser QA covers navigation, surface toggles, notes panel, keyboard focus, and responsive layout.

## Todo items

- [ ] Add teacher-facing `slide_deck` labels to artifact progress/status UI.
- [ ] Load student, teacher, and print surfaces in the existing approval preview lifecycle.
- [ ] Add slide navigation, position, optional outline/thumbnails, notes panel, and surface toggles.
- [ ] Add scoped feedback controls for deck, slide, block, and interaction targets.
- [ ] Show optional online-media warnings when `requires_network` metadata is present.
- [ ] Run browser QA for navigation, toggles, notes panel, keyboard focus, responsive behavior, and student-surface leak safety.

## Blocked by

- SD-04 slide surfaces and answer-leak-safe projection.
- SD-07 scoped slide_deck regeneration from teacher feedback.

## References

- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `apps/web/src/components/teaching-packs-artifact-progress.tsx`
- `apps/web/src/components/teaching-packs-content-approval-body.tsx`
- `services/gateway/routers/teaching_packs.py`

## Implementation notes

- Use `visual-engineering`/frontend review discipline for this issue.
- Keep preview sandbox constraints intact; do not combine iframe sandbox flags unsafely.
- Avoid adding manual teacher controls that can force arbitrary component placement in v1.
