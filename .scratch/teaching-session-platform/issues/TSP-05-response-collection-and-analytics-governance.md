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

## Amendment (2026-07-07 — design interview decisions)

- [ ] Gamification, if enabled, is **non-competitive**: private per-student points/streaks (each student sees only their own), or whole-class collective points — never a public individual leaderboard/rank. Opt-in per teacher preference, consistent with the non-competitive framing already established in the effectiveness-loop dashboard (no vendor-stat-style comparative display).
- [ ] Raw session response capture ships now (structured, `kc_ids`-tagged per `effectiveness-loop/el-001`'s outcome data model) — but **no new analytics/insights dashboard is built on this data in v1**. `effectiveness-loop/el-003` (capture) is audited as "honestly not-done, so the loop runs on synthetic air" — this capture is designed to become that real input once `effectiveness-loop` is made real, rather than building a second, parallel fake analytics layer.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-02-join-and-role-token-model.md
