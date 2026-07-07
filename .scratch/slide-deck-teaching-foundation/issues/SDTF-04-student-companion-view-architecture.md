---
title: Student companion view architecture for slide decks
status: ready-for-agent
labels: [ready-for-agent, slide-deck, frontend]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Design the future student runtime as a mobile-readable companion view keyed by slide and interaction IDs, rather than only mirroring the projector slide. This slice should define the architecture and minimal projection contract needed for companion cards while keeping v1 exports standalone and local-only.

The work should not implement live sync, student join, authentication, or response persistence. It should ensure the slide-deck surface model can later support companion prompts, vocabulary scaffolds, exit tickets, and read-only current-slide fallback without exposing teacher-only data.

## Acceptance criteria

- [ ] Companion view architecture is documented or represented in projection contracts as separate from projector presentation.
- [ ] Student companion data is derived from the same student-safe projection and cannot include teacher-only notes or answer keys.
- [ ] Mobile readability is a first-class requirement; student view is not forced into tiny 16:9 projector scaling.
- [ ] Interaction IDs are sufficient to bind future companion cards to slide prompts.
- [ ] Current v1 behavior remains standalone/local-only with no student-response persistence.
- [ ] Real-LLM acceptance can inspect at least student-safe companion-readable content shape when this surface is implemented.

## Blocked by

- SDTF-01-session-ready-ids-and-interaction-contract.md
- SDH-02-safe-projections-and-chrome-policy.md
