---
title: Add slide-native teacher preview UX inside the existing approval gate
status: done
labels: [slide-deck-engine, frontend, teacher-gate, done]
created: 2026-07-06
---

## Parent

ADR-042.

## What to build

Adapt the existing teacher approval experience so `slide_deck` remains a normal artifact in progress/status lists but opens a slide-native preview when reviewed. The preview should help teachers assess the deck as a presentation, not as one long HTML document.

The UX should include slide navigation, current slide position, optional outline/thumbnail rail where feasible, teacher notes/facilitation panel, student/teacher/print surface toggles, warnings for optional online media, and scoped feedback controls that can target deck, slide, block, or interaction.

This slice must reuse the existing teacher gate lifecycle and approval actions. It must not silently bypass compliance or create a second approval workflow.

## Acceptance criteria

- [x] `slide_deck` appears in artifact progress/status displays with clear teacher-facing label.
- [x] Approval preview can load student presentation, teacher guide, and print surfaces for the same slide deck snapshot.
- [x] Teacher notes and answer guidance appear only in teacher surface/panel.
- [x] Student surface preview does not contain teacher-only notes or answer data.
- [x] Scoped feedback controls capture target level and stable target ID where available.
- [x] Online media warnings are visible in teacher preview when a deck contains `requires_network` media.
- [x] Browser QA covers navigation, surface toggles, notes panel, keyboard focus, and responsive layout.

## Todo items

- [x] Add teacher-facing `slide_deck` labels to artifact progress/status UI.
- [x] Load student, teacher, and print surfaces in the existing approval preview lifecycle.
- [x] Add slide navigation, position, optional outline/thumbnails, notes panel, and surface toggles.
- [x] Add scoped feedback controls for deck, slide, block, and interaction targets.
- [x] Show optional online-media warnings when `requires_network` metadata is present.
- [x] Run browser QA for navigation, toggles, notes panel, keyboard focus, responsive behavior, and student-surface leak safety.

## Completion notes

- Added the slide-native approval preview inside the existing content-approval gate, preserving the current gate lifecycle and edit action.
- Added `slide_deck` teacher-facing artifact labeling, slide outline/navigation, current slide position, student/teacher/print surface toggles, teacher notes panel, online-media warnings, and scoped feedback payloads for deck/slide/block/interaction targets.
- Added backend print-preview support through the existing rendered snapshot preview endpoint with teacher/admin authorization for teacher and print surfaces.
- Verified focused backend/frontend behavior with `uv run pytest services/gateway/tests/test_teaching_pack_previews.py -q` → `9 passed`, `pnpm --dir apps/web exec vitest run tests/teaching-pack-slide-deck-preview.test.tsx tests/teaching-pack-section-editor.test.tsx` → `6 passed`, and `pnpm --dir apps/web typecheck` → passed.
- Browser QA used a temporary local Next.js route with the SD-08 deck fixture, then removed the route. Verified slide navigation, student/teacher/print surface URL switching, teacher-only notes hidden on student/print and visible on teacher, online-media warnings, scoped interaction feedback target payload, keyboard focus on controls, and responsive layouts at 375px, 768px, and desktop width. The temporary route's iframe returned expected unauthenticated 401s for mock snapshot URLs; endpoint behavior is covered by the backend preview tests.

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
