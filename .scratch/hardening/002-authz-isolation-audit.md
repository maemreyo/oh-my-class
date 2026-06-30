---
title: Tenant isolation audit and ownership-scoping enforcement
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Harden and prove teacher data isolation. The pattern is already good — `teaching_pack_store.get_run(run_id, teacher_id)` scopes by `teacher_id` in the query and `_get_run_with_ownership` + `require_teacher` guard routers — but an unscoped `get_run_by_id(run_id)` exists (internal/executor use) and must never back a teacher-facing endpoint. New unit endpoints must follow the scoped pattern.

- Make **store-level ownership scoping the rule**: teacher-facing reads/writes go through `teacher_id`-scoped accessors; the unscoped `get_run_by_id` is restricted to internal callers (executor/worker/orchestrator).
- A lint/test that **no teacher-facing router** calls the unscoped accessor; unit/child endpoints (ADR-017) reuse `_get_run_with_ownership` rather than ad-hoc checks.
- Defense-in-depth: keep both the store-level `WHERE teacher_id` and the router `require_teacher` dependency.
- A cross-teacher test matrix across all teacher-facing endpoints: run, artifacts, snapshots, notifications, approvals/resume, and units.

## Acceptance criteria

- [ ] Teacher-facing endpoints resolve runs only via `teacher_id`-scoped accessors; `get_run_by_id` is internal-only.
- [ ] A lint/test fails if a teacher-facing router uses the unscoped accessor.
- [ ] Unit/child endpoints reuse the shared ownership helper; no ad-hoc ownership checks.
- [ ] A cross-teacher matrix proves teacher A cannot read or act on teacher B's run/artifact/snapshot/notification/unit (404/403).

## Detailed test suite

(Real DB + real gateway app; two teachers.)

- [ ] `services/gateway/tests/test_tenant_isolation_matrix.py`: for every teacher-facing endpoint, teacher B accessing teacher A's resource is denied (404/403).
- [ ] `services/gateway/tests/test_no_unscoped_accessor_in_routers.py`: a static/lint check finds no teacher-facing router calling `get_run_by_id`.
- [ ] `services/gateway/tests/test_unit_ownership.py`: unit read/action endpoints enforce ownership via the shared helper.
- [ ] Run `uv run pytest services/gateway/tests/test_tenant_isolation_matrix.py services/gateway/tests/test_no_unscoped_accessor_in_routers.py services/gateway/tests/test_unit_ownership.py -v`.

## Blocked by

None - can start immediately
