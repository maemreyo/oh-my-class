---
title: Editor route, local draft buffer, and explicit-commit save
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, frontend]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decisions 10, 11)

## What to build

Wire the editor into the app at `/runs/[runId]/decks/[deckId]/edit` (full-screen, own layout — not the existing narrow-column run-status page). Edits buffer client-side and mirror to `localStorage` (reusing SDH-03's precedent) for crash recovery; exactly one request creates a new version, on explicit "Save" or navigation-away — no autosave-per-keystroke.

## Acceptance criteria

- [ ] Route exists at `/runs/[runId]/decks/[deckId]/edit`, keeps `run_id` for ownership/lineage scoping, and does not inherit the dashboard's run-status page chrome.
- [ ] In-progress edits are mirrored to `localStorage` continuously; reloading/crashing the tab and returning restores the unsaved draft.
- [ ] Exactly one SDE-04 endpoint call is made per explicit "Save" action or on navigating away with unsaved changes (with a confirm prompt) — never one call per field change.
- [ ] Draft state is cleared from `localStorage` only after a successful save.
- [ ] A 409 optimistic-lock conflict (SDE-04) surfaces a clear "someone/something changed this deck, reload to continue" message rather than a silent failure.

## Blocked by

- SDE-03-structured-visual-block-editor.md
- SDE-04-edit-api-versioning-and-concurrency.md
