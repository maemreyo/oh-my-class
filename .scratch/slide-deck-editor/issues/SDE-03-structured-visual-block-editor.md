---
title: Structured-visual block editor (no freeform WYSIWYG)
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, frontend]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decisions 3, 11)

## What to build

Build the in-browser editing canvas: teachers click directly on rendered slide content, but every editable region maps 1:1 to a registry-defined block field (SDE-02) — no arbitrary HTML/CSS entry. This is a new, purpose-built React component tree operating directly on `SlideDeckData`, completely separate from `packages/renderer/src/slide-deck-projection.ts` (which keeps its existing read-only display/export role, untouched).

## Acceptance criteria

- [ ] Each registry block type (heading, bullet list, image+caption, quiz_check, etc.) has its own React component supporting both read-mode and edit-mode.
- [ ] Editing a field only accepts values matching that field's registry type/constraints (e.g. max bullet count, heading length for density guard) — no raw HTML acceptance path exists anywhere in the editor.
- [ ] `slide-deck-projection.ts` has zero new dependents from this work; its existing exported functions and their tests are unchanged.
- [ ] Each block-type component has its own focused test (well-tested per-component, not one giant editor test).
- [ ] The editor renders at `/runs/[runId]/decks/[deckId]/edit` as a dedicated full-screen route (own layout, not the dashboard's narrow-column run-status chrome).

## Blocked by

- SDE-02-slide-capability-registry-full-contract.md
- SDTF-01-session-ready-ids-and-interaction-contract.md (stable block IDs needed for click-target mapping)
