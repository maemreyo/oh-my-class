---
title: Live teaching cockpit for slide-deck sessions
status: ready-for-agent
labels: [ready-for-agent, teaching-session, frontend]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Design the teacher live-session UI as a teaching cockpit, not a dense analytics dashboard. During class, the teacher needs current slide/activity, pacing, next action, class-level signal, and one-tap branch options. Deeper analytics can wait for post-lesson review.

This slice should define the cockpit information architecture and UX states for live, degraded/offline, recovering, and ended sessions. It should preserve the existing slide deck presentation surface and student-safe projection boundaries.

## Acceptance criteria

- [ ] Live cockpit prioritizes current activity, next action, pacing, class signal, and branch options.
- [ ] The UI avoids raw response walls and student ranking by default.
- [ ] The cockpit can show degraded/offline/reconnecting states without blocking standalone presentation.
- [ ] Teacher-only notes and AI suggestions are visible only to controller/teacher roles.
- [ ] Branch actions are teacher-controlled and map to validated branch content or gated suggestions.
- [ ] Post-lesson analytics are treated as a separate deeper view.
- [ ] The design is usable under classroom pressure with minimal reading and clear next actions.

## Amendment (2026-07-07 — design interview decisions)

- [ ] Live annotation/whiteboard overlay is **ephemeral only** in v1 — drawings clear on slide change/session end, with no save/persist path and no retention-tier interaction.
- [ ] A pacing nudge (comparing elapsed time to SDTF-02's `planned_duration_minutes`) is available but **opt-in per teacher preference**, stored via the existing per-teacher/class memory pattern (`priority-upgrades/002`) — not a default-on alert.

## Blocked by

- TSP-02-join-and-role-token-model.md
- TSP-03-event-log-sync-and-recovery.md
