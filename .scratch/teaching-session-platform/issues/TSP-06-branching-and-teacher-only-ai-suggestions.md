---
title: Precomputed branching and teacher-only AI suggestions
status: ready-for-agent
labels: [ready-for-agent, teaching-session, slide-deck]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Design live-session branching so teachers can respond to class understanding without showing raw AI output directly to students. The platform should prefer precomputed, quality-validated branches such as reteach, hint, simpler example, or challenge extension. On-the-fly AI is teacher-facing, async, auditable, and requires teacher approval plus safety/quality checks before students see it.

## Acceptance criteria

- [ ] Branch content types are specified: reteach, hint, simpler example, challenge, extra practice.
- [ ] Precomputed branches can attach to deck/slide/interaction IDs and pass normal quality/projection gates.
- [ ] Teacher cockpit can surface branch options without forcing immediate generation during class.
- [ ] On-the-fly AI suggestions are teacher-only drafts by default.
- [ ] No raw AI output streams directly to student/display surfaces.
- [ ] Teacher approval and safety/quality gating are required before generated branch content becomes student-visible.
- [ ] Branch selection is recorded as a session event for evidence/post-lesson reflection.

## Blocked by

- TSP-03-event-log-sync-and-recovery.md
- TSP-04-live-teaching-cockpit.md
- TSP-05-response-collection-and-analytics-governance.md
