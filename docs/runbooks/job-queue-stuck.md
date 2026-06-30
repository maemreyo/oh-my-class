# Runbook: Job Queue Stuck / Stale Leases

## Symptom

- Runs remain in `running` status indefinitely; no progress events are emitted.
- `queue_depth` SLO dimension exceeds `OMC_SLO_MAX_QUEUE_DEPTH` (default 25).
- Jobs show `lease_expires_at` in the past but `status = 'running'` — the worker that claimed the lease has crashed or lost connectivity.
- Sweeper background task is not running (gateway started without the sweeper lifespan hook).

## Alert

SLO breach fires via `dispatch_slo_alerts` in `services/gateway/slo_alerting.py` when
`queue_depth > max_queue_depth`.
Alert key: `global:queue_depth`.
Delivered to `OMC_SLO_SLACK_WEBHOOK_URL` / `OMC_SLO_ZALO_WEBHOOK_URL`.

## Diagnosis

1. Query stale leases:
   ```sql
   SELECT job_id, run_id, status, attempts, lease_owner, lease_expires_at, created_at
   FROM public.run_jobs
   WHERE status = 'running' AND lease_expires_at < NOW()
   ORDER BY created_at;
   ```
2. Check that the background sweeper is running in the gateway process:
   ```
   grep "sweep_stuck_jobs" <gateway log> | tail -20
   ```
   The sweeper (`services/gateway/recovery_sweeper.py`) runs on a periodic interval
   configured in the gateway lifespan.
3. Check for worker crashes: look for `ProcessLookupError`, `BrokenPipeError`, or
   unhandled exceptions in the gateway log around the time leases expired.
4. Confirm `eligible_at` on `QUEUED` jobs is in the past (they should be claimable):
   ```sql
   SELECT job_id, status, eligible_at FROM public.run_jobs
   WHERE status IN ('queued', 'pending') AND eligible_at <= NOW()
   ORDER BY eligible_at;
   ```

## Remediation

1. **Automatic path**: the sweeper (`sweep_stuck_jobs`) runs on its scheduled interval and:
   - Resets jobs with `attempts < DEFAULT_MAX_ATTEMPTS` (3) to `PENDING` — clears `lease_owner`
     and `lease_expires_at` so a worker can re-claim.
   - Sets jobs with `attempts >= DEFAULT_MAX_ATTEMPTS` to `FAILED`.
   The `eligible_at` index (`ix_run_jobs_status_eligible_at`) ensures workers pick up
   re-queued jobs efficiently.

2. **Manual immediate trigger** (if sweeper interval is too long):
   ```
   POST /ops/sweep
   ```

3. **Force-reset a specific stuck job** (use sparingly — bypasses attempt counter):
   ```sql
   UPDATE public.run_jobs
   SET status = 'pending', lease_owner = NULL, lease_expires_at = NULL
   WHERE job_id = '<job_id>';
   ```

4. If the sweeper itself is not running, restart the gateway:
   ```
   systemctl restart omc-gateway   # or equivalent process manager
   ```

## Escalation

- If `queue_depth` stays above threshold after sweeper runs, check for a DB connectivity
  issue or a bug in the worker claim logic.
- If jobs are permanently stuck at `attempts >= 3`, investigate the root cause before
  manually resetting `attempts`.
- Page on-call if more than 10 runs are affected simultaneously.

## Verify

1. Confirm no stale leases remain:
   ```sql
   SELECT COUNT(*) FROM public.run_jobs
   WHERE status = 'running' AND lease_expires_at < NOW();
   ```
   Expected: 0.
2. Confirm queue depth normalises: `GET /ops/slo` → `queue_depth <= 25`.
3. Confirm affected runs resume processing (new events appear in `run_events`).
