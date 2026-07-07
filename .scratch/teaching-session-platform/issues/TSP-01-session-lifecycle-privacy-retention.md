---
title: TeachingSession lifecycle, privacy, and retention policy
status: ready-for-agent
labels: [ready-for-agent, teaching-session, slide-deck]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Define the future `TeachingSession` lifecycle and privacy-retention model for delivering slide decks. A session should bind to an immutable deck snapshot and progress through clear lifecycle states such as scheduled, live, ended, archived, or expired. Storage policy must be explicit and privacy-first.

This slice should design the model and boundaries; it does not need to implement full live delivery. It must make clear that raw individual responses are not persisted by default and that aggregate/minimal retention is the K-12-safe baseline.

## Acceptance criteria

- [ ] A `TeachingSession` lifecycle is specified with allowed states and transitions.
- [ ] Sessions bind to `deck_id`, `snapshot_id`, and stable slide/block/interaction IDs without mutating deck snapshots.
- [ ] Retention levels are specified: none, aggregate, pseudonymous, identifiable.
- [ ] Default K-12 policy is aggregate/minimal retention, not raw identifiable responses.
- [ ] Retention policy is visible to teacher/admin surfaces and can be included in evidence.
- [ ] Session data categories are separated: events, aggregates, raw responses, teacher reflections, AI suggestions, and exports.
- [ ] Future deletion/export requirements are documented without implementing a full privacy portal in this slice.

## Blocked by

None - can start immediately
