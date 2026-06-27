---
title: Pipeline V2 notifications and safe admin recovery
status: ready-for-agent
labels: [pipeline-v2, notifications, admin, recovery]
created: 2026-06-27
order: 14
blocked_by: [ISSUE-002-production-persistence, ISSUE-003-control-plane-executor, ISSUE-012-auth-governance-versioning, ISSUE-013-operations-hardening]
adr_refs:
  - docs/adr/011-operational-hardening.md
  - docs/adr/012-data-governance-and-versioning.md
---

## Problem

Teachers need to know when input is required or a run completes/fails, and operators need safe recovery tools for failed, stuck, or escalated runs. Relying only on the dashboard being open is insufficient.

## Scope

Implement first-class in-app notifications and minimal admin recovery APIs/UI hooks.

Agent-ready tasks:

1. Add notification event and delivery record models.
2. Implement in-app notification channel.
3. Define channel adapter interface for future email/Zalo/Telegram.
4. Emit notifications for clarification required, contract confirmation, search confirmation, blueprint ready, content preview ready, run completed, run failed, run escalated, and gate timeout warning.
5. Implement safe admin run summary API.
6. Implement admin list filters for failed, stuck, escalated, timed out, and awaiting long-running gates.
7. Implement safe recovery action registry: retry stuck job, retry failed artifact, retry notification, cancel run, re-open current gate, mark escalated.
8. Record admin actor, action, reason, and result.

## Out Of Scope

- Full admin console design.
- External notification channels.
- Arbitrary stage jump or direct DB/state editor.

## Acceptance Criteria

- In-app notifications are persisted, idempotent, and visible to the correct teacher/admin.
- Notification delivery records prevent duplicate spam.
- Admin can inspect safe summaries without raw prompts, raw fetched pages, or student PII.
- Admin recovery actions are limited to the safe registry.
- Every recovery action is audited.

## Required Edge Cases And Tests

- Duplicate notification event creates one delivery per recipient/channel.
- Notification for soft-deleted run is hidden or revoked.
- Teacher cannot see another teacher's notifications.
- School admin sees organization-scoped notifications only.
- Retry notification action does not duplicate already-delivered notification unless explicitly forced by safe action.
- Admin retry failed artifact respects idempotency and artifact workflow state.
- Admin cannot replay old gate response or mutate contract silently.
- Safe run summary redacts student evidence and answer keys unless role and view allow them.
- Trace links are absent gracefully if Langfuse is down or disabled.

## Test Plan

- Real Postgres tests for notification delivery records and admin action audit.
- API auth tests for teacher/school_admin/system_admin.
- UI hook/component tests for in-app notification list and admin summary if implemented in this issue.
- Recovery action tests for allowed and forbidden actions.

## Observability

- Persist events for notification queued, delivered, failed, dismissed, recovery action requested, recovery action completed, and recovery action denied.

## Rollback

If external channel adapters are incomplete, keep them disabled. In-app notification and safe recovery APIs are required for production V2.
