---
title: Real evidence harness for TeachingSession platform behavior
status: ready-for-agent
labels: [ready-for-agent, teaching-session]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Define and eventually implement a real evidence harness for TeachingSession behavior. The harness should prove session lifecycle, role tokens, sync/recovery, response retention, teacher cockpit signals, branch selection, and delivery modes with actual deck snapshots and realistic classroom flows.

When generation is involved, the harness must use real gateway/model flow consistent with ADR-044. When testing session behavior, it should use real HTTP/SSE surfaces rather than only unit tests.

## Acceptance criteria

- [ ] Evidence scenarios cover at least live classroom, offline/degraded presentation fallback, and review/homework delivery mode.
- [ ] Evidence records session ID, deck ID, snapshot ID, role tokens used, delivery mode, retention policy, and final lifecycle state.
- [ ] Evidence proves controller/display/student/observer roles cannot access unauthorized surfaces or teacher-only data.
- [ ] Evidence proves SSE/current-state recovery or equivalent real sync path, including reconnect behavior.
- [ ] Evidence proves idempotent student submissions and aggregate-default analytics behavior.
- [ ] Evidence proves teacher-only AI suggestions or branch options do not reach student surfaces without teacher approval.
- [ ] Evidence bundles avoid secrets and unnecessary PII.
- [ ] The harness exits non-zero if any required real session behavior fails.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
- TSP-02-join-and-role-token-model.md
- TSP-03-event-log-sync-and-recovery.md
- TSP-05-response-collection-and-analytics-governance.md
