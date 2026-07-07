---
title: Delivery modes and teacher-confirmed feedback loop
status: ready-for-agent
labels: [ready-for-agent, teaching-session]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Define delivery modes over the same immutable deck snapshot: live, homework, review, flipped, and catch-up. Each mode should control navigation, response collection, sync, and retention policy without confusing those policies with visual display preferences.

Post-lesson analytics should produce teacher-confirmed recommendations, not automatic regeneration. Recommendations may include reteach mini-deck, practice worksheet, homework, or next-lesson adjustment, but the teacher approves before generation or assignment.

## Acceptance criteria

- [ ] Delivery modes are specified separately from display preferences.
- [ ] Live mode is teacher-controlled; review/homework/flipped/catch-up can be student-paced according to policy.
- [ ] Each mode defines default response, retention, and sync behavior.
- [ ] Post-lesson recommendations cite aggregate/concept evidence rather than raw student data by default.
- [ ] Recommendations require teacher approval before generation, assignment, or sharing.
- [ ] Generated follow-up content uses existing teaching-pack generation/quality pathways rather than a separate auto-generation silo.
- [ ] Evidence records delivery mode, retention mode, and recommendation decisions.

## Amendment (2026-07-07 — design interview decisions)

- [ ] v1 implements the `live` delivery mode only. `homework`/`review`/`flipped`/`catch-up` are explicitly out of v1 implementation scope (they are async-assignment shaped: no SSE, no room code, no live cockpit).
- [ ] The `delivery_mode` field/enum is declared in the session schema for all five modes now, even though only `live` has a working implementation — so adding the async modes later is not a breaking schema change.
- [ ] Post-lesson sharing with parents/guardians, if built, is **teacher-mediated only**: the teacher generates and shares a non-identifiable aggregate "class recap" (see TSP-09) — direct parent access to individual student data is out of scope, since it would require reopening the anonymous-first identity model (TSP-01/02) for a new third party and deserves its own ADR if pursued.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-05-response-collection-and-analytics-governance.md
