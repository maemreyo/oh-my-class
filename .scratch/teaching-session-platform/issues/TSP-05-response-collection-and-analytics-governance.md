---
title: Response collection and analytics governance for TeachingSession
status: ready-for-agent
labels: [ready-for-agent, teaching-session]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Define response collection and analytics governance for future slide-deck sessions. Quick checks should be structured-first. Free text is allowed only in explicit interaction modes and must pass PII/safety filtering before storage or analytics. Analytics should default to class-concept and misconception-level insight, with group or individual views only when identity and retention policy allow.

## Acceptance criteria

- [ ] Supported response kinds are specified with structured-first defaults.
- [ ] Free text is gated by interaction type, session policy, and safety/PII filtering.
- [ ] Response retention levels align with TSP-01: none, aggregate, pseudonymous, identifiable.
- [ ] Default analytics are class-concept/misconception aggregate, not individual ranking.
- [ ] Group or individual drill-down requires explicit identity/retention policy.
- [ ] Analytics outputs can feed post-lesson recommendations without exposing unnecessary raw responses.
- [ ] Student local-only exports remain non-persistent and do not accidentally call response APIs.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-02-join-and-role-token-model.md
