---
title: Pedagogical component registry alignment for slide decks
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Align slide decks with the broader component-strategist direction so decks are built from typed pedagogical components rather than freeform LLM slide patterns. Examples include worked example, misconception check, think-pair-share, vocabulary scaffold, guided practice, recap, and exit ticket.

This slice should identify the minimum component registry shape needed for slide decks and how components map to slide roles, density expectations, accessibility requirements, teacher guidance, and renderer behavior. It should not require a full component strategist rollout if that is not ready.

## Acceptance criteria

- [ ] Slide-deck roles/components are mapped to a small typed teaching-component vocabulary.
- [ ] Each component defines expected student-facing content, teacher-only guidance, density/accessibility checks, and renderer needs.
- [ ] LLM generation is constrained to validated component choices or shapes, not arbitrary untyped slide patterns.
- [ ] Quality gates can evaluate component completeness for at least the required slide spine.
- [ ] The approach is compatible with existing component-strategist ADRs and does not create a parallel registry silo.
- [ ] Real-LLM evidence includes component coverage for the required deck spine before this foundation is considered done.

## Blocked by

- SDTF-02-pedagogical-roles-and-planned-pacing.md
