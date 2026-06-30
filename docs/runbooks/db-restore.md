# Runbook: DB Restore

See the full disaster recovery procedure in
[docs/operations/disaster-recovery.md](../operations/disaster-recovery.md).

This runbook summarises the operational steps and the verification gate.

## Symptom

- Gateway is unable to connect to Postgres, or data corruption / accidental deletion
  is detected in `public.runs`, `public.run_jobs`, `public.gate_interrupts`,
  `public.gate_responses`, `public.run_status_history`, or LangGraph checkpoint tables.
- All run endpoints return 500 or DB connection errors.
- Data audits show missing or inconsistent rows (e.g. a run with no matching `run_jobs`).

## Alert

Not directly emitted by `slo_alerting.py` — a full DB outage prevents SLO metrics from
being computed. The symptom is a gateway health-check failure:

```
GET /health  →  503
```

Monitor the health endpoint and page on-call immediately on 503.

## Diagnosis

1. Confirm Postgres connectivity from the gateway host:
   ```
   psql "$DATABASE_URL" -c "SELECT 1;"
   ```
2. If the DB is reachable, check for data loss:
   ```sql
   -- Example: runs with no associated jobs
   SELECT r.run_id FROM public.runs r
   LEFT JOIN public.run_jobs j ON j.run_id = r.run_id
   WHERE j.job_id IS NULL AND r.status NOT IN ('completed', 'failed', 'cancelled');
   ```
3. Identify the last good backup:
   - Managed snapshots: check the cloud provider's snapshot console.
   - Manual dumps: check the offsite encrypted dump location.
   - RPO: 6 hours (1 hour with PITR enabled).
4. Determine the extent of data loss: compare the restore point timestamp against
   the most recent `created_at` in affected tables.

## Remediation

Follow the full restore procedure from
[docs/operations/disaster-recovery.md — Restore procedure](../operations/disaster-recovery.md#restore-procedure):

1. Stop gateway workers and scheduled sweepers.
2. Restore the app Postgres snapshot or dump into a clean database.
3. Restore the Langfuse Postgres snapshot or dump.
4. Run Alembic migrations against the restored app database:
   ```
   uv run alembic upgrade head
   ```
5. Start the gateway:
   ```
   WORKER_MODE=in_process uvicorn services.gateway.main:app
   ```
6. Verify `/health`, `/ops/slo`, and admin run listing respond correctly.
7. Resume any interrupted run at an active teacher gate:
   ```
   POST /teaching-packs/runs/{run_id}/resume
   ```
   Confirm a new resume job is enqueued (`QUEUED` status in `run_jobs`).

The automated restore drill is in
`services/gateway/tests/test_checkpoint_recovery.py` — it exports and restores
run, status-history, active-gate, and job rows, then verifies the resume flow
through FastAPI. Run it after a restore to validate data integrity:
```
uv run pytest services/gateway/tests/test_checkpoint_recovery.py -v
```

## Escalation

- If the restore takes longer than the 2-hour RTO target: page additional on-call engineers.
- If Langfuse analytics restore is needed: allow up to 4 hours total (see disaster-recovery.md).
- If PITR is available and RPO < 6 hours: use PITR to the latest point before the incident.
- Contact cloud provider support if managed snapshot restore fails.

## Verify

1. `GET /health` → 200.
2. `GET /ops/slo` → all SLO dimensions within thresholds.
3. Confirm run counts match expectations:
   ```sql
   SELECT status, COUNT(*) FROM public.runs GROUP BY status;
   ```
4. Resume a previously interrupted run and confirm it advances through the pipeline.
5. Confirm the automated drill passes:
   ```
   uv run pytest services/gateway/tests/test_checkpoint_recovery.py -v
   ```
