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

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-05-response-collection-and-analytics-governance.md
