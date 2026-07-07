---
title: System-provided deck structure presets
status: ready-for-agent
labels: [ready-for-agent, slide-deck, feature]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision

## What to build

Offer a small set of system-curated structural presets (e.g. "5E model," "direct instruction," "flipped intro") a teacher can pick as a starting point for a new deck. These are **not** teacher-saved custom templates derived from their own decks — that would require `SlideDeckEngine` phase-level checkpoint/resume capability that doesn't exist today and isn't otherwise needed. Personalized templates are explicitly deferred until the engine gains that capability for another reason (e.g. partial-failure recovery).

## Acceptance criteria

- [ ] A fixed, curated list of structural presets is available at deck-creation time, each mapping to a specific `PedagogicalPlanner`/`SlideArchitecturePlanner` configuration.
- [ ] No mechanism exists for a teacher to save an arbitrary existing deck's structure as a new preset in this slice.
- [ ] Preset selection is optional; the default (no preset) generation path is unaffected.
- [ ] Adding a new system preset later does not require a schema change (presets are configuration, not new contract types).

## Blocked by

None — can start once SDE-01/02 land.
