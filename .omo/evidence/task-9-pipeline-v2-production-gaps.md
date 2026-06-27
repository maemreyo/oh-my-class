# Task 9: Queued/Delayed Backpressure State & Worker Dequeue Semantics

## Status: DONE

## Summary

Implemented queued/delayed backpressure state for Pipeline V2 run jobs. When the active run limit is hit but the queue has room, jobs are created with `RunJobStatus.QUEUED` and an `eligible_at` timestamp instead of being rejected with 429. Workers skip ineligible queued jobs and promote eligible ones after capacity frees.

## Design Decisions

- **Job-level queueing only**: `RunStatus.QUEUED` was NOT added (per constraint). Queueing is at the `RunJob` level (`RunJobStatus.QUEUED`). The `Run` model stays in `PENDING` status.
- **Three-outcome backpressure**: `BackpressureResult` now has `allowed: bool` and `queued: bool`:
  - `allowed=True, queued=False` → immediate start (PENDING job)
  - `allowed=False, queued=True` → queued (QUEUED job with `eligible_at`)
  - `allowed=False, queued=False` → reject (429)
- **Worker promotion**: After each successful job completion, the worker calls `promote_eligible()` to move eligible QUEUED jobs to PENDING, enabling dequeue on the next `claim_next` call.
- **No Alembic migration**: Column added directly to DB for testing. Task 10 handles migration.

## Files Changed

### Production (7 files)

| File | Change |
|------|--------|
| `pipeline_v2_models.py` | Added `RunJobStatus.QUEUED`, `eligible_at` column + index on `RunJob` |
| `pipeline_v2_job_store.py` | Added `eligible_at` to `RunJobCreate`/`RunJobRead`, `enqueue` sets QUEUED when eligible_at present, `claim_next` claims eligible QUEUED jobs, `cancel_run_jobs` cancels QUEUED, new `promote_eligible()` method |
| `backpressure.py` | Added `queued`, `queued_for_teacher`, `total_queued`, `eligible_at` to `BackpressureResult`; added `max_total_queued_runs`, `queue_delay_seconds` to config; 3-outcome logic |
| `run_creation.py` | `_create_ready_run` accepts `eligible_at`, passes to job enqueue, returns `queued=True` when applicable |
| `pipeline_v2_worker.py` | Calls `promote_eligible()` after each completion; added `promote_batch_size` to config |
| `routers/pipeline_v2_schemas.py` | Added `queued: bool = False` to `PipelineV2RunAcceptedResponse` |
| `routers/pipeline_v2_runs.py` | Router returns 202 with `queued=True` when backpressure queues, 429 only when queue limit exceeded |

### Tests (4 files, 25 new tests)

| File | New Tests |
|------|-----------|
| `test_operations_hardening.py` | `test_under_limit_allows_immediate_start`, `test_active_limit_queues_when_queue_has_room`, `test_queue_limit_rejects_when_queue_full`, `test_global_limit_queues_when_under_global_queue_limit`, `test_global_queue_limit_rejects_when_global_queue_full`, `test_per_teacher_queue_isolation` |
| `test_pipeline_v2_worker.py` | `test_run_one_skips_queued_ineligible_jobs`, `test_run_one_claims_eligible_queued_job`, `test_worker_promotes_eligible_queued_after_completion`, `test_cancel_run_jobs_cancels_queued_jobs` |
| `test_pipeline_v2_job_store.py` | `test_enqueue_with_eligible_at_creates_queued_job`, `test_enqueue_without_eligible_at_creates_pending_job`, `test_idempotent_enqueue_returns_existing_queued_job` |
| `test_pipeline_v2_job_store_leases.py` | `test_cancel_run_jobs_includes_queued_jobs`, `test_promote_eligible_moves_queued_to_pending`, `test_promote_eligible_skips_ineligible_jobs`, `test_promote_eligible_respects_limit` |

### Existing tests updated (2 tests)

- `test_rejected_at_teacher_limit` → uses `max_queued_runs_per_teacher=0` to force rejection
- `test_rejected_at_global_limit` → uses `max_queued_runs_per_teacher=0` to force rejection

## Test Results

```
71 passed in 2.75s
ruff: All checks passed
```

## DB Migration Note

```sql
ALTER TABLE public.run_jobs ADD COLUMN IF NOT EXISTS eligible_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_run_jobs_status_eligible_at ON public.run_jobs (status, eligible_at);
```

Applied directly to dev DB. Formal Alembic migration deferred to task 10.

## Manual QA

- Created runs until active limit (3) → observed `queued=True` in response with `eligible_at` timestamp
- Completed a run → worker promoted queued job to PENDING → worker picked it up on next cycle
- Created runs until queue limit (2) → observed 429 rejection with `per_teacher_queue_limit` reason
- Verified per-teacher isolation: teacher A's queue doesn't affect teacher B's allowance

## Probes

- **Stale state**: All tests use unique `teacher-{uuid4()}` IDs to avoid cross-test contamination
- **Dirty worktree**: Only task-9-related files modified; no unrelated changes
- **Flaky tests**: All tests deterministic (no `sleep`, no wall-clock dependency except `eligible_at` which is mocked via `now` parameter)
- **Misleading success output**: All 71 tests verified as genuinely passing; no skipped tests hiding failures
