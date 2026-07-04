# [OPS-11] Poison-run dead-letter + replay

Status: TODO
Labels: ops, resilience
ADR: 034
Depends on: OPS-04

## Context

Retry today is unbounded-ish and terminal-vague. `requeue_with_backoff` sets a job back to
`QUEUED` with a delay (`services/gateway/teaching_pack_job_store.py:147-165`), transient errors
are classified via `TransientProviderError` (`packages/llm_client/errors.py`), and the recovery
sweeper resets stuck jobs until `attempts >= max_attempts`, at which point it sets status
`FAILED` (`services/gateway/recovery_sweeper.py:42-65`, `DEFAULT_MAX_ATTEMPTS`). `RunJobStatus`
has `PENDING/QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED` (`services/gateway/models.py:44-53`) —
**no dead-letter state**.

Two problems at scale:
1. A **permanent** (non-transient) failure still burns the full retry budget before landing in
   `FAILED`, wasting latency budget and capacity.
2. `FAILED` is a dead end: there is no *inspectable, replayable* holding state for ops to
   examine a poison run, fix the root cause, and replay it. A poison run can silently consume
   worker slots via repeated re-claims.

This is **infra-poison**, which is distinct from **quality-escalate** (ADR-029): quality
escalation is a human-review path for content that failed the quality bar and is surfaced to the
teacher via the explainable gate; infra-poison is an operational failure (provider permanent
error, bad input, code bug) that ops must triage. They must not be conflated.

## Scope

- [ ] Add a **dead-letter state** to `RunJobStatus` (e.g. `DEAD_LETTER`) in
      `services/gateway/models.py` + Alembic migration. Dead-lettered jobs are removed from the
      claimable pool (exclude from `claim_next` / `list_pending`) so they never re-consume slots.
- [ ] **Bounded retries with classification**:
      - Transient (`TransientProviderError` and peers): retry with capped backoff up to a hard
        ceiling N; on exhausting N → dead-letter.
      - Permanent (non-transient / classified-terminal): **immediate** dead-letter, no retry.
      Centralize this decision in the worker's error handling
      (`services/gateway/teaching_pack_worker.py`) so both the worker path and the sweeper agree.
- [ ] Persist **dead-letter metadata**: last error, error classification, attempt count,
      timestamps, and enough context to triage (run_id, stage, provider). Inspectable via an
      ops/admin endpoint (system_admin scope).
- [ ] **Replay**: an ops-triggered action that re-enqueues a dead-lettered job (reset to
      `pending`, clear lease, reset/annotate attempts) after the root cause is fixed. Replay must
      be idempotent-safe (rides on OPS-10 side-effect idempotency) so a replayed run does not
      duplicate exports/events.
- [ ] **Page alert** on dead-letter growth via the OPS-04 tiered alerting (DLQ growth is a
      page-level SLO signal per ADR-034 decision 2). Emit a metric/event the alert rule watches.
- [ ] **Surface to teacher + ops**: the teacher sees the run as "failed — needs attention" (a
      clear, non-alarming state distinct from a quality-escalate notice); ops sees it in the
      dead-letter inspection view. Reuse the existing run-status surfacing; add the new state to
      the teacher-facing status mapping without collapsing it into quality-escalate.
- [ ] Keep **distinct from quality-escalate**: do not route infra-poison through the ADR-029
      escalation/gate path; do not send a quality-escalate notification for an infra failure.
      Add a guard test asserting the two paths stay separate.

## Acceptance

- A permanent provider error dead-letters the job **immediately** (0 retries), removed from the
  claimable pool — proven with a fault-injection test.
- A transient error retries with capped backoff and dead-letters only after exactly N attempts —
  proven by counting attempts.
- Dead-lettered jobs are never re-claimed by `claim_next` or reset by the sweeper.
- An ops replay re-runs a dead-lettered job to success with **no duplicate side effects**
  (rides OPS-10).
- Dead-letter growth fires a **page** alert (OPS-04); p95/queue warnings stay separate.
- The teacher sees "failed — needs attention"; a guard test proves infra-poison never triggers
  the quality-escalate (ADR-029) path and vice versa.

## References

- `services/gateway/teaching_pack_job_store.py:147-165` — `requeue_with_backoff`.
- `services/gateway/recovery_sweeper.py:33-65` — `sweep_stuck_jobs`, `DEFAULT_MAX_ATTEMPTS`.
- `services/gateway/teaching_pack_worker.py` — worker error handling / re-claim.
- `packages/llm_client/errors.py` — `TransientProviderError` classification.
- `services/gateway/models.py:44-53` — `RunJobStatus` enum (no dead-letter today).
- `services/gateway/tests/test_permanent_failure_fails.py`,
  `services/gateway/tests/test_operations_hardening.py` — existing failure-path tests to extend.
- OPS-04 (SLO + tiered alerting) — page rule for DLQ growth.
- OPS-10 (idempotency) — safe replay.
- ADR-029 (quality escalation) — the path this must stay distinct from.
- ADR-034 decisions 2 and 7.

## Implementation notes

- Classification is the hinge: reuse `TransientProviderError` as the transient predicate and treat
  everything else as terminal unless explicitly whitelisted as retryable.
- Dead-letter is a *holding* state, not a *terminal* one — the whole point is inspect-fix-replay.
  Keep `FAILED` for genuinely-terminal/cancelled cases and reserve `DEAD_LETTER` for triage.
- Bound the blast radius: dead-lettering must exclude the job from every claimable query
  (`claim_next`, `list_pending`, sweeper reset) atomically to stop slot consumption.
- Replay is an *ops* affordance (system_admin), not a teacher affordance.
