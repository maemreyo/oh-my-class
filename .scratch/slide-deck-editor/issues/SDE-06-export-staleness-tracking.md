---
title: Versioned exports and re-export-needed indicator
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, backend]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 8)

## What to build

Every export records the `snapshot_id` it was generated from and remains valid/accessible after later edits (never silently overwritten or invalidated). The editor shows a "re-export needed" indicator when the latest export's snapshot lags the deck's current snapshot; re-export is always a manual teacher action.

## Acceptance criteria

- [ ] Export records persist their source `snapshot_id`; an edit never deletes or overwrites a prior export.
- [ ] The editor UI compares the latest export's `snapshot_id` to the deck's current `snapshot_id` and shows a staleness badge/indicator when they differ.
- [ ] No automatic re-export is triggered by an edit — re-export only happens on explicit teacher action.
- [ ] Older, still-valid exports remain reachable/downloadable after newer edits exist.

## Blocked by

- SDE-04-edit-api-versioning-and-concurrency.md
