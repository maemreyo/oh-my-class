---
title: Session-ready slide IDs and interaction contract
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Harden the slide-deck content model so future teaching sessions can bind to immutable deck snapshots without changing the generated content shape later. The deck, slides, blocks, and interactions need stable identifiers and interaction metadata that can support future response collection while remaining local-only and non-persistent in the current release.

This slice should not add a live session runtime or student response storage. It should make the existing slide deck contract explicitly session-ready: stable IDs, typed interaction kinds, answer-bearing flags, no-JS fallback, accessibility label, and teacher-only guidance that remains projection-gated.

## Acceptance criteria

- [ ] Deck, slide, block, and interaction identifiers are stable enough to serve as future session join points.
- [ ] Interactions are typed and include prompt, response intent, answer-bearing flag, no-JS fallback, and accessibility label where applicable.
- [ ] Teacher-only answer guidance remains separated from student/presentation projections.
- [ ] Standalone/student exports do not persist student responses or include response collection endpoints.
- [ ] The model can express quick check, discussion prompt, exit ticket, and short-answer style interactions without arbitrary HTML/JS.
- [ ] Real-LLM evidence shows generated interactions are meaningful and safe in at least one scenario before claiming this foundation slice done.

## Blocked by

None - can start immediately
