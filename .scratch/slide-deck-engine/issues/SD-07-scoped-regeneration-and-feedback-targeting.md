---
title: Support scoped slide_deck regeneration from teacher feedback
status: ready-for-agent
labels: [slide-deck-engine, teacher-gate, regeneration, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-040 and ADR-042.

## What to build

Enable teacher feedback on `slide_deck` to target the deck, a slide, a block, or an interaction, and regenerate the narrowest safe scope while preserving accepted sibling artifacts and accepted slide content.

This slice should integrate with the existing scoped rejection/regeneration semantics of the teaching-pack graph. It should not introduce a separate slide workflow. Feedback target maps, stable IDs, source refs, and engine trace artifacts should make scoped repair deterministic and explainable.

## Acceptance criteria

- [ ] Teacher feedback payloads can identify deck-level, slide-level, block-level, and interaction-level targets using stable IDs.
- [ ] Scoped regeneration of one slide preserves other slides unless a plan-level dependency requires broader regeneration.
- [ ] Scoped regeneration of `slide_deck` preserves accepted non-slide artifacts when their dependencies remain valid.
- [ ] The engine records whether the repair was block, slide, plan, or full-deck scoped and why.
- [ ] If a scoped repair would violate objective coverage, pacing, teacher-only separation, or density policies, the engine escalates scope predictably.
- [ ] Tests cover rejecting slide 4 for density, rejecting an interaction for answer-leak risk, and deck-level style/tone feedback.

## Todo items

- [ ] Extend teacher feedback payloads with deck, slide, block, and interaction target identifiers.
- [ ] Wire targeted feedback into existing scoped regeneration semantics for `slide_deck`.
- [ ] Preserve accepted sibling slides and non-slide artifacts when dependencies remain valid.
- [ ] Record repair scope and escalation rationale in engine trace metadata.
- [ ] Add deterministic escalation when scoped repair breaks coverage, pacing, teacher-only separation, or density policy.
- [ ] Add tests for density rejection, interaction answer-leak rejection, and deck-level style/tone feedback.

## Blocked by

- SD-06 engine quality, typed healing, scorecard, and observability.

## References

- `docs/adr/020-langgraph-send-artifact-fanout.md`
- `docs/adr/029-healing-escalation-to-teacher-review.md`
- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `packages/agents/teaching_pack/scoped_regeneration.py`
- `packages/agents/teaching_pack/artifact_fanout.py`
- `packages/agents/teaching_pack/quality_routing.py`

## Implementation notes

- Do not rebuild a parallel regeneration path for slides.
- Treat stable IDs as a user-facing/teacher-feedback contract once surfaced.
- Preserve accepted artifacts unless the existing graph semantics require regeneration.
