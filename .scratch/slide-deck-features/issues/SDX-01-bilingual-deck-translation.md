---
title: Bilingual (EN <-> VI) deck translation
status: ready-for-agent
labels: [ready-for-agent, slide-deck, feature, llm]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 4, deck-level exception)

## What to build

Add a "Dịch deck này" action that creates a new, independent deck (own immutable snapshot, own version lineage) translated between English and Vietnamese, reusing the `ContentMaterializer` LLM step (SDE-01) applied across all blocks in one pass. Scoped to EN<->VI only — matching the ESL scenario already confirmed via ADR-044's Vietnamese localization test — not a general multi-language framework.

## Acceptance criteria

- [ ] Translation produces a **new** deck (new `deck_id`/snapshot lineage), never overwrites the source deck.
- [ ] Only text content is translated 1:1 per block; layout, block structure, and media are unchanged — this is why it's allowed to run at deck scope despite ADR-047's block-level rewrite boundary (it doesn't touch `layout_composition`/`slide_architecture`).
- [ ] Only English<->Vietnamese is supported; no generic language-selector framework is built.
- [ ] Translated output passes the same registry/density/accessibility validators as any other `ContentMaterializer` output.
- [ ] The translated deck records a reference to its source deck (which snapshot it was translated from), without copying answer-key or teacher-only content beyond what the source deck itself exposes.

## Blocked by

- SDE-01-content-materialization-llm-integration.md
