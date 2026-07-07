---
title: Related artifact reference foundation for slide decks
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Let slide decks safely reference related teaching-pack artifacts without copying those artifacts or leaking answer keys. A deck should be able to say that a slide connects to a worksheet, quiz, drill, lesson objective, or assessment checkpoint by stable ID or semantic target. Future teaching sessions can use those references as launch points, but this slice only establishes safe reference semantics.

## Acceptance criteria

- [ ] Slide/block metadata can reference related artifacts or objectives by stable ID or semantic target.
- [ ] Related references do not embed whole worksheet/quiz content or answer keys into the deck.
- [ ] Student/presentation projections expose only safe relationship labels or links when appropriate.
- [ ] Teacher preview can show related artifact context for planning.
- [ ] Missing related artifacts degrade gracefully without breaking standalone deck export.
- [ ] Real-LLM evidence or fixture replay proves references do not create student-facing answer leakage.

## Blocked by

- SDTF-01-session-ready-ids-and-interaction-contract.md
