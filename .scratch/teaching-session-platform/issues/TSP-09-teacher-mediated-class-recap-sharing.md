---
title: Teacher-mediated, non-identifiable class recap sharing
status: ready-for-agent
labels: [ready-for-agent, teaching-session, privacy]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery (Amendment, decision 29 / TSP-07)

## What to build

Let a teacher generate and share a short, non-identifiable, aggregate recap of a completed session ("Lớp mình học được X hôm nay, phần Y làm tốt") via a link or export, to keep parents/guardians informed without exposing per-student data.

This is deliberately **not** a parent portal or per-student progress view. The teacher remains the sole gatekeeper of what leaves the system; no new parent-facing auth/identity model is introduced. Direct, per-student parent access is out of scope for this issue (it would require reopening the anonymous-first identity model in TSP-01/02 and deserves its own ADR if ever pursued).

## Acceptance criteria

- [ ] Recap content is generated only from session-level aggregate data (retention tier `aggregate` or coarser) — never from `identifiable`/`pseudonymous`-tier per-student records, even if that tier was enabled for the session.
- [ ] The teacher explicitly triggers recap generation and reviews/edits the text before it can be shared (teacher-confirmed, same principle as ADR-046 decision 19).
- [ ] Sharing is via a link or export the teacher controls (e.g., copy-to-clipboard, download) — no new parent account, login, or persistent access grant is created.
- [ ] The recap contains no student names, IDs, or individually-identifying performance data.
- [ ] Recap generation is logged as a session event for audit purposes (what was shared, when, by whom), without storing the shared content as new PII-bearing state.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-05-response-collection-and-analytics-governance.md
- TSP-07-delivery-modes-and-feedback-loop.md
