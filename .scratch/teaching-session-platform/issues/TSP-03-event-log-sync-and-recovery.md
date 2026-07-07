---
title: TeachingSession event log, sync transport, and recovery
status: ready-for-agent
labels: [ready-for-agent, teaching-session]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Design the event, sync, and recovery foundation for future live TeachingSessions. Significant session actions should be append-only events, while the UI reads a derived current-state model. Live broadcast should be SSE-first, with REST POST for student responses/actions, polling fallback, and WebSocket deferred until collaboration requires it.

The design must support classroom reliability: teacher/projector reloads, student reconnects, duplicate submissions, and network drops.

## Acceptance criteria

- [ ] Significant event types are specified: session started, slide changed, interaction opened, aggregate updated, branch selected, annotation added, session ended.
- [ ] Derived read models are specified for fast teacher/display/student UI state.
- [ ] Sync transport policy is specified: SSE broadcast, REST POST actions/responses, polling fallback, WebSocket deferred.
- [ ] Reconnect flow uses session ID and role token to fetch current derived state.
- [ ] Event resume via last event ID is specified where possible.
- [ ] Student submissions use idempotency keys to prevent duplicate responses.
- [ ] Offline standalone presentation remains a supported fallback when live sync is unavailable.
- [ ] Retention policy from TSP-01 governs whether raw response events are retained, aggregated, or pruned.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-02-join-and-role-token-model.md
