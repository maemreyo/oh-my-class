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

## Amendment (2026-07-07 — design interview decisions)

- [ ] Retention/purge is implemented now as a session-scoped `is_prunable()`-style predicate (fail-closed default-deny, scheduled-sweeper cadence), deliberately mirroring `OPS-07-data-lifecycle-retention.md`'s shape without depending on it or waiting for it (that epic is `Status: TODO` in an unscheduled track).
- [ ] A TSP-specific FERPA/COPPA/Vietnam Decree-13 (PDPD) compliance addendum is authored now, scoped to data collected directly from student devices during a session — a different consent/data-flow story than `PRIV-01`'s teacher-submitted `student_evidence` — written to merge into `PRIV-01`'s eventual compliance doc rather than diverge permanently.
- [ ] Retention tier (none/aggregate/pseudonymous/identifiable) is chosen once at session creation, cannot silently escalate mid-session, and choosing `identifiable` requires an explicit on-screen acknowledgment persisted to the data-access audit trail.
- [ ] `pseudonymous`/`identifiable` tiers are only selectable when the session is bound to a real, org-scoped `class_id` — never for an anonymous open-join room.

## Blocked by

None - can start immediately
