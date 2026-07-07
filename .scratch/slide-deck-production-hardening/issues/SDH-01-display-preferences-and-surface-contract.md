---
title: Slide deck display preferences and surface contract
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries

## What to build

Introduce a typed slide-deck-specific display preference contract that lets the app, gateway, renderer, and standalone HTML agree on the active surface and display options without letting the LLM decide layout or chrome. The slice should preserve the existing slide-deck content model and add the narrowest production seam for defaults, runtime overrides, and effective export settings.

The display contract should cover the v1 decisions from ADR-043: surfaces (`presentation`, `student`, `teacher`, `print`, `review`), print layout (`paged`, `continuous`), slides per page (`1`, `2`, `4`, `6`), and chrome visibility (`hidden`, `minimal`, `branded`). It should be slide-deck-specific, strict, and easy to extend later for paper size/orientation without exposing those controls in v1.

## Acceptance criteria

- [ ] A typed slide-deck display preference shape exists at the appropriate contract boundary and has strict defaults for missing values.
- [ ] Renderer-side TypeScript has a matching strict type/schema or parser, with no loose `metadata.printLayout` string lookups scattered across the codebase.
- [ ] Defaults match ADR-043: standalone export opens presentation-safe, student chrome is hidden/minimal, print supports paged/continuous with valid slides-per-page values only.
- [ ] Existing slide-deck generation remains content-focused; no LLM prompt/output field is responsible for choosing display preferences.
- [ ] Effective preferences can be passed from preview/export surfaces without breaking existing slide-deck artifacts that do not yet contain the new preference fields.
- [ ] Technical guard tests cover defaulting, invalid option rejection/fallback, and backward-compatible rendering of an existing deck.
- [ ] Real-LLM acceptance evidence is not required for this slice alone unless it changes gateway/export behavior; final feature acceptance remains blocked by SDH-07.

## Blocked by

None - can start immediately
