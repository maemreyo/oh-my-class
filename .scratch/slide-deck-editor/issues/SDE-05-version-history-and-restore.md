---
title: Linear version history with restore (no diff UI)
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, frontend]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 7)

## What to build

Expose the immutable snapshot lineage created by SDE-04 as a simple, linear, restorable list — not a diff/rollback UI. Teachers can view any past version read-only and restore it (creating a new version that copies the old content).

## Acceptance criteria

- [ ] Version list shows timestamp, editor identity, and a short label (e.g. "Manual edit," "AI rewrite: shorter") per version, newest first.
- [ ] Any past version can be opened read-only.
- [ ] "Restore this version" creates a brand-new version copying the selected version's content — it never mutates or deletes intervening versions.
- [ ] No side-by-side diff/comparison view is built in this slice (explicitly deferred).
- [ ] Version list pagination/scroll works reasonably for decks with many edits (no unbounded single-page render).

## Blocked by

- SDE-04-edit-api-versioning-and-concurrency.md
