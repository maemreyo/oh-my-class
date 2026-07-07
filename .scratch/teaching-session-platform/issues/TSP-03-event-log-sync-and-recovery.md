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

## Amendment (2026-07-07 — design interview decisions)

- [ ] Live broadcast uses Redis Pub/Sub (already running in this stack for LiteLLM cache), not an extension of the single-listener in-memory event bus — a session-id-keyed channel lets any gateway instance publish and any instance's SSE handler relay to its own connected students.
- [ ] Any new Redis-backed path here ships with a live-path-proof test per ADR-032 — `packages/agents/healing/redis_breaker_store.py` (Redis-backed, zero runtime callers per the 2026-07-01 audit) is the cautionary example not to repeat.
- [ ] Session state is Redis-hot (current slide, roster, tallies) with a Postgres write-behind event log; on Redis restart/failover, a session reconstructs state by replaying the last N Postgres events — this is the concrete mechanism behind "event resume."
- [ ] When live sync is unreachable, the session degrades to SDH-03's existing standalone/offline player rather than failing — teaching continues, only live interaction collection pauses, and it auto-resumes syncing when connectivity returns.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-02-join-and-role-token-model.md
