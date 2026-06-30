# Runbook: Provider Down / Free-Tier Exhausted

## Symptom

- Runs stall in `running` status; LLM calls return 429 or 5xx errors from the upstream provider.
- `success_rate` SLO dimension drops below `OMC_SLO_MIN_SUCCESS_RATE` (default 0.95).
- `run_latency_p95_seconds` SLO dimension exceeds `OMC_SLO_MAX_RUN_LATENCY_P95_SECONDS` (default 900 s).
- Log lines contain `RateLimitedError` or provider HTTP 429/503.

## Alert

SLO breach fires via `dispatch_slo_alerts` in `services/gateway/slo_alerting.py` when
`success_rate < min_success_rate` or `run_latency_p95_seconds > max_run_latency_p95_seconds`.
Payload delivered to `OMC_SLO_SLACK_WEBHOOK_URL` / `OMC_SLO_ZALO_WEBHOOK_URL`.
Alert key: `global:success_rate` or `global:run_latency_p95_seconds`.

## Diagnosis

1. Check gateway logs for `RateLimitedError` or `AgentError` with a 429/503 body.
2. Confirm the provider dashboard (OpenRouter / direct provider) shows quota exhaustion or an outage.
3. Query stuck jobs:
   ```sql
   SELECT job_id, status, attempts, lease_expires_at
   FROM public.run_jobs
   WHERE status = 'running' AND lease_expires_at < NOW();
   ```
4. Inspect `OMC_SLO_*` env vars to confirm thresholds match expectations.

## Remediation

1. **If free-tier exhausted**: upgrade the provider plan or rotate to a paid API key
   (`OMC_OPENROUTER_API_KEY` or equivalent), then restart the gateway workers.
2. **If transient outage**: wait for provider recovery. The sweeper will automatically
   reclaim stuck jobs once `lease_expires_at` passes (see `sweep_stuck_jobs` in
   `services/gateway/recovery_sweeper.py`):
   - Jobs with `attempts < 3` are reset to `PENDING` and re-queued (lease cleared, `attempts` incremented).
   - Jobs with `attempts >= 3` are set to `FAILED`.
3. To trigger immediate re-queue without waiting for the sweeper interval, call the admin endpoint:
   ```
   POST /ops/sweep
   ```
4. Verify `QUEUED`/`PENDING` jobs resume processing once the provider is available.

## Escalation

- If outage exceeds 30 minutes or affects all teachers: page the on-call engineer.
- If a run has `attempts >= 3` and must be retried manually, reset via:
  ```sql
  UPDATE public.run_jobs SET status = 'pending', attempts = 0, lease_owner = NULL, lease_expires_at = NULL
  WHERE job_id = '<job_id>';
  ```
- Contact provider support if quota increase or incident SLA is needed.

## Verify

1. Confirm no jobs stuck in `running` with expired leases:
   ```sql
   SELECT COUNT(*) FROM public.run_jobs
   WHERE status = 'running' AND lease_expires_at < NOW();
   ```
   Expected: 0.
2. Confirm `success_rate` SLO recovers: `GET /ops/slo` should show `success_rate >= 0.95`.
3. Trigger a test run and confirm it completes within the latency SLO.
