---
title: Pipeline V2 notifications and safe admin recovery
status: review-partial
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

## Ultrawork Review — 2026-06-27

Status: PARTIAL. In-app notifications and safe admin recovery primitives exist, but external channels/admin UI hooks are intentionally limited.

Evidence:
- Notification models and migration exist in `services/gateway/notification_models.py`, `notification_db.py`, and `alembic/versions/008_notifications.py`.
- Notification store/channel logic is implemented in `services/gateway/notification_store.py` and `notifications.py`; routes are in `services/gateway/routers/notifications.py`.
- Safe recovery actions are implemented in `services/gateway/admin_recovery.py` and audited through persisted run events.
- Tests cover notification dedupe/delivery/read/dismiss/isolation, admin recovery actions, audit events, and auth edges in `services/gateway/tests/test_notifications_admin_recovery.py`.
- Active safe recovery registry now includes `retry_notification`. It retries only failed/pending notification deliveries for the run, marks the selected delivery `delivered`, and does not duplicate already-delivered delivery records.
- Focused retry-notification verification: red regression first failed on missing `SafeRecoveryAction.RETRY_NOTIFICATION`; after implementation, `uv run pytest services/gateway/tests/test_notifications_admin_recovery.py -q -k "retry_notification or recovery_emits_audit_event"` → `3 passed`; `uv run basedpyright services/gateway/admin_recovery.py services/gateway/tests/test_notifications_admin_recovery.py` → `0 errors`; `uv run python -m py_compile services/gateway/admin_recovery.py services/gateway/tests/test_notifications_admin_recovery.py` → success; manual DB-backed driver verified `execute_recovery(... RETRY_NOTIFICATION ...)` marks a failed in-app delivery delivered.
- Admin run listing now supports operational filters for `failed`, `stuck`, `escalated`, `timed_out`, and `awaiting_gate` through `services/gateway/admin_run_filters.py` and `/notifications/admin/runs?operational_filter=...`.
- Focused admin-list verification: route regressions first exposed missing operational filtering and legacy malformed status-row leakage; after implementation/refactor, `uv run pytest services/gateway/tests/test_notifications_router_admin.py -q` → `3 passed`; `uv run basedpyright services/gateway/admin_run_filters.py services/gateway/routers/notifications.py services/gateway/tests/test_notifications_router_admin.py` → `0 errors`; `uv run python -m py_compile services/gateway/admin_run_filters.py services/gateway/routers/notifications.py services/gateway/tests/test_notifications_router_admin.py` → success; manual TestClient driver verified `operational_filter=failed&teacher_id=...` returns the failed run through the admin route.
- Active notification helper emitters are now verified for the broad backend event set. `services/gateway/tests/test_notifications_admin_recovery.py::TestNotificationHelpers::test_all_pipeline_event_helpers_emit_notifications` covers contract confirmation, search confirmation, blueprint ready, content preview ready, run escalated, and gate timeout warning; adjacent helper tests cover clarification/gate-required, run completed, and run failed.
- Focused notification-emitter verification: `uv run pytest services/gateway/tests/test_notifications_admin_recovery.py::TestNotificationHelpers::test_all_pipeline_event_helpers_emit_notifications -q` → `1 passed`; `uv run basedpyright services/gateway/notifications.py services/gateway/tests/test_notifications_admin_recovery.py` → `0 errors`; `uv run python -m py_compile services/gateway/notifications.py services/gateway/tests/test_notifications_admin_recovery.py` → success. Manual surface is the helper layer writing real in-app notifications/delivery records through the notification store.
- Active Teaching Pack completion/failure notification wiring is now verified at the executor persistence seam. `TeachingPackFailureRecorder` and `TeachingPackCompletionRecorder` accept a narrow notification sink; `InAppTeachingPackNotificationSink` calls the existing in-app helper emitters; `services/gateway/main.py` wires that sink into the live background worker recorders.
- Focused executor-notification verification: red recorder regressions first failed because the recorders had no notification sink; after implementation and splitting completion-recorder code/tests into focused files, `uv run pytest services/gateway/tests/test_teaching_pack_executor.py services/gateway/tests/test_teaching_pack_completion.py -q` → `11 passed`; `uv run basedpyright services/gateway/teaching_pack_executor.py services/gateway/teaching_pack_completion.py services/gateway/teaching_pack_executor_types.py services/gateway/main.py services/gateway/tests/test_teaching_pack_executor.py services/gateway/tests/test_teaching_pack_completion.py` → `0 errors`; `uv run python -m py_compile services/gateway/teaching_pack_executor.py services/gateway/teaching_pack_completion.py services/gateway/teaching_pack_executor_types.py services/gateway/main.py services/gateway/tests/test_teaching_pack_executor.py services/gateway/tests/test_teaching_pack_completion.py` → success. Manual surface is executor recorder persistence invoking the same in-app notification sink used by the gateway worker.

Gaps:
- Webhook routes still contain TODOs for Telegram/Zalo processing in `services/gateway/routers/webhooks.py`, which is acceptable only because external channels are out of scope.
- Full admin console UI is not present, and admin summary UI hooks are not proven beyond backend primitives. Backend `retry_notification` recovery is now covered.
- Notification event helper emitters are now verified for contract/search/blueprint/content-preview/escalation/timeout plus the previously covered gate-required/completed/failed helpers. Completion/failure helper wiring is now verified through the active executor recorders and gateway worker. Wiring from every graph stage to every approval helper remains broader workflow evidence.
- Full admin UI coverage for the admin list/filter endpoint is still not present; backend filters are now covered.
