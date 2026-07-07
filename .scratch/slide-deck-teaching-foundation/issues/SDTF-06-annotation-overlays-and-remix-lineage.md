---
title: Annotation overlays and remix lineage for slide decks
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Define the future-safe model for teacher annotations and deck remix without mutating generated deck snapshots. Generated snapshots should remain immutable. Teacher annotations, highlights, notes, and future live markings should attach as overlays keyed by slide/block IDs. Remix actions should derive new snapshots with lineage rather than rewriting existing content.

This slice is primarily a foundation/contract/documentation slice unless implementation seams already exist. It must not introduce arbitrary HTML/CSS/JS editing.

## Acceptance criteria

- [ ] Deck snapshots are treated as immutable content versions.
- [ ] Annotation concepts are modeled or documented as overlays keyed by stable slide/block IDs.
- [ ] Teacher annotations are teacher-only by default; student visibility requires explicit future live-session action.
- [ ] Remix is modeled as derived snapshot lineage, not mutation of existing snapshots.
- [ ] Display preferences/export attempts are explicitly separate from content version lineage.
- [ ] Manual future edits are constrained to structured patches or regeneration targets, not arbitrary HTML/CSS/JS.
- [ ] Acceptance criteria for future implementation require quality/projection revalidation after any content-affecting remix or edit.

## Blocked by

- SDTF-01-session-ready-ids-and-interaction-contract.md
