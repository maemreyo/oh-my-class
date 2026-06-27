---
title: Pipeline V2 idempotency, job leases, cancellation, budgets, and backpressure
status: ready-for-agent
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
