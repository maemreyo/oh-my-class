---
title: Pipeline V2 idempotency, job leases, cancellation, budgets, and backpressure
status: review-partial
labels: [pipeline-v2, operations, idempotency, jobs, budgets]
created: 2026-06-27
order: 13
blocked_by: [ISSUE-002-production-persistence, ISSUE-003-control-plane-executor, ISSUE-012-auth-governance-versioning]
adr_refs:
  - docs/adr/011-operational-hardening.md
---

## Problem

V2 background execution needs reliable behavior under duplicate requests, stale gates, worker crashes, cancellation, provider timeouts, queue pressure, and runaway retries.

## Scope

Implement operational hardening primitives.

Agent-ready tasks:

1. Add idempotency records for create, resume, cancel, retry, and admin recovery actions.
2. Add explicit Postgres `run_jobs` table with lease owner, lease expiry, heartbeat, attempts, and status.
3. Implement worker lease renewal and recovery sweeper.
4. Implement `POST /run/{run_id}/cancel` with actor/reason persistence.
5. Implement stuck/timed-out/escalated status transitions.
6. Implement gate timeout escalation and notification; never auto-approve.
7. Implement run, stage, artifact, LLM, search, fetch, healing, and concurrency budgets from RunContract.
8. Implement tenant/user active and queued run limits.
9. Implement queue backpressure responses and UI-visible delayed/queued status.
10. Add budget ledger/event records.

## Out Of Scope

- External queue infrastructure.
- Arbitrary admin stage jumps.
- Billing or paid-provider accounting.

## Acceptance Criteria

- Duplicate idempotent requests do not duplicate runs, gate responses, jobs, artifacts, snapshots, or events.
- Worker crash/lease expiry can recover safely.
- Cancellation stops future work and marks status consistently.
- Gate timeout escalates/notifies and never self-approves.
- Budget exceedances follow hard-fail/degrade/HITL policy.
- Queue pressure is visible and does not produce long HTTP waits.

## Required Edge Cases And Tests

- Same idempotency key + same body returns same result.
- Same idempotency key + different body rejects.
- Missing idempotency key behavior is explicit and tested.
- Worker dies before persisting stage result, after persisting result before event, and after event before job completion.
- Lease expires while original worker is still alive; only one worker can commit final stage result.
- Cancel during LLM call stops subsequent stages once call returns.
- Cancel during awaiting gate marks gate closed and rejects later resume.
- Budget degradation reduces fetches/parallelism and records why.
- Active run limit blocks or queues new runs with user-friendly status.
- Healing loop stops at configured cap and escalates.
- Recovery sweeper is idempotent.

## Test Plan

- Real Postgres concurrency tests using parallel transactions.
- Executor tests with simulated worker crash and lease expiry.
- API tests for cancel, duplicate resume, stale gate, and queue pressure.
- Live 9Router smoke for timeout/degrade path where feasible.

## Observability

- Persist events for idempotency hit/conflict, job leased, heartbeat missed, lease expired, job recovered, budget degraded, budget exceeded, cancel requested, cancelled, stuck, timed out, escalated.

## Rollback

Operational hardening is required for V2 production. If implementation is incomplete, do not expose V2 to real users.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Job leases, sweeper, budgets, backpressure, cancellation, and idempotency are implemented/tested, but full crash timing and live timeout/degrade proof are incomplete.

Active-surface reconciliation: the historical review below names `pipeline_v2_*` job/worker/router files. The active operational surface is `services/gateway/teaching_pack_job_store.py`, `teaching_pack_worker.py`, `teaching_pack_executor.py`, active cancellation/lifecycle routers, and shared recovery/budget/backpressure modules where still used by the Teaching Pack flow.

Evidence:
- Job table and lease fields are in migration `services/gateway/alembic/versions/004_pipeline_v2_run_jobs.py` and model `services/gateway/pipeline_v2_models.py`.
- Job store, worker, recovery sweeper, leases, budgets, and backpressure are implemented in `pipeline_v2_job_store.py`, `pipeline_v2_worker.py`, `recovery_sweeper.py`, `worker_lease.py`, `budget.py`, and `backpressure.py`.
- Idempotency helpers are in `services/gateway/pipeline_v2_idempotency.py`; cancel route behavior is in `services/gateway/routers/pipeline_v2_runs.py`.
- Tests cover job idempotency, lease reclaim, worker execution/failure, sweeper behavior, budgets, active run limits, and cancellation in `services/gateway/tests/test_pipeline_v2_job_store.py`, `test_pipeline_v2_job_store_leases.py`, `test_pipeline_v2_worker.py`, `test_operations_hardening.py`, and `test_pipeline_v2_runs_router_edges.py`.
- Active Teaching Pack budget ledger persistence now includes replayable event evidence. `services/gateway/budget_db.py` persists ledgers and can emit `teaching_pack.budget.ledger_recorded` internal events with a compact tokens/searches/fetches/retries payload.
- Focused budget verification: `uv run pytest services/gateway/tests/test_budget_db.py -q` → `5 passed`; `uv run basedpyright services/gateway/budget_db.py services/gateway/tests/test_budget_db.py` → `0 errors`; `uv run python -m py_compile services/gateway/budget_db.py services/gateway/tests/test_budget_db.py` → success; manual driver verified `budget_ledger_payload` and `write_budget_ledger_event` module surfaces.
- Active Teaching Pack cancellation actor/reason persistence is now verified at the public route surface. `services/gateway/routers/teaching_pack_lifecycle.py` already persisted `teaching_pack.run.cancelled` with `actor_id`, `reason`, and `cancelled_jobs`; `services/gateway/tests/test_teaching_pack_lifecycle.py` now drives `POST /teaching-packs/run/{run_id}/cancel` and asserts the stored `RunEvent.payload`, cancelled job count, final run status, and SSE replay.
- Focused cancel verification: `uv run pytest services/gateway/tests/test_teaching_pack_lifecycle.py -q` → `1 passed`; `uv run basedpyright services/gateway/tests/test_teaching_pack_lifecycle.py` → `0 errors`; `uv run python -m py_compile services/gateway/tests/test_teaching_pack_lifecycle.py` → success. The first focused run usefully exposed missing status-stream auth override in the route-test harness while the new DB event payload assertion passed; the focused lifecycle harness now matches the active stream route dependency.
- Active Teaching Pack cancellation now closes active gates and blocks stale resume after cancel. `TeachingPackControlStore.cancel_active_gates()` marks active gates `cancelled`; the public cancel route calls it and records `cancelled_gates` in `teaching_pack.run.cancelled` payload.
- Focused cancel-active-gate verification: red lifecycle regression first proved cancelled awaiting-gate runs still accepted resume with `202`; after the fix, `uv run pytest services/gateway/tests/test_teaching_pack_lifecycle.py -q` → `2 passed`; `uv run basedpyright services/gateway/teaching_pack_control_store.py services/gateway/routers/teaching_pack_lifecycle.py services/gateway/tests/test_teaching_pack_lifecycle.py` → `0 errors`; `uv run python -m py_compile services/gateway/teaching_pack_control_store.py services/gateway/routers/teaching_pack_lifecycle.py services/gateway/tests/test_teaching_pack_lifecycle.py` → success. Manual surface is public cancel followed by public resume returning `409 stale_gate`, with persisted gate status `cancelled`.
- Active gateway startup recovery sweeper wiring is now verified. `services/gateway/main.py` already starts `_run_teaching_pack_sweeper` inside FastAPI `lifespan` alongside `_run_teaching_pack_worker`; `services/gateway/tests/test_main.py` now replaces the placeholder test with a lifespan regression proving both background tasks are scheduled through the startup surface.
- Focused sweeper-wiring verification: `uv run pytest services/gateway/tests/test_main.py -q` → `1 passed`; `uv run basedpyright services/gateway/tests/test_main.py` → `0 errors`; `uv run python -m py_compile services/gateway/tests/test_main.py` → success. Manual surface is `gateway_main.lifespan(app)` with patched background-task sentinels.
- Active Teaching Pack backpressure visibility is now route-tested. `services/gateway/routers/teaching_pack_runs.py` already returns `queued: true` in the accepted response when active limits are saturated but queue capacity remains; `services/gateway/tests/test_teaching_pack_backpressure_routes.py` drives `POST /teaching-packs/run` with saturated active limits and asserts the UI-visible queued response plus persisted `RunJobStatus.QUEUED` job.
- Focused backpressure-route verification: `uv run pytest services/gateway/tests/test_teaching_pack_backpressure_routes.py -q` → `1 passed`; `uv run basedpyright services/gateway/tests/test_teaching_pack_backpressure_routes.py` → `0 errors`; `uv run python -m py_compile services/gateway/tests/test_teaching_pack_backpressure_routes.py` → success. Manual surface is the public FastAPI create route returning `queued: true` without long request waiting.

Gaps:
- I found simulated lease/recovery tests, not full crash timing proof for every specified point between stage result, event, and job completion.
- Live 9Router timeout/degrade behavior was not found.
- Recovery sweeper functions and periodic background wiring in `services/gateway/main.py` are now startup-tested.
- Cancel route behavior and actor/reason persistence in the cancel event payload are now route-tested on the active Teaching Pack surface.
- Cancel during awaiting gate now closes active gates and rejects later resume on the active Teaching Pack surface.
- Budget ledger persistence/event recording is now verified for the active Teaching Pack budget store seam. Remaining budget gaps: healing budget, concurrency budget, and budget degradation behavior through live provider paths.
- Backpressure rejects over-limit requests and the active queued-state path is now verified through the public Teaching Pack create route. Full UI rendering of queued/delayed state remains broader UI/UX cutover work.
