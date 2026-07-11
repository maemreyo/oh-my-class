# Disaster recovery

Critical state is Postgres-backed. Redis is cache/coordination only and is safe to lose; workers rebuild queue visibility from `public.run_jobs`, run rows, active gates, and LangGraph checkpoints.

## Backup scope

- App Postgres database: `public.runs`, `public.run_jobs`, `public.gate_interrupts`, `public.gate_responses`, `public.run_status_history`, LangGraph checkpoint tables, class profiles, outcome/mastery tables, artifact snapshots, and notification tables.
- Langfuse Postgres database: traces, scores, datasets, and annotations.
- Redis: no backup. It is configured as ephemeral state and must not be treated as the source of truth.

## Cadence, retention, and offsite

- Base cadence: managed snapshot or `pg_dump` every 6 hours for app Postgres and Langfuse Postgres.
- Retention: 48 hourly restore points, 14 daily restore points, 8 weekly restore points.
- Offsite: copy encrypted dumps/snapshots to a separate cloud account or region immediately after creation.
- Restore drill cadence: monthly, plus before any real-classroom production launch.

## RPO/RTO

- RPO: 6 hours in normal operation; 1 hour after classroom launch if managed PITR is enabled.
- RTO: 2 hours for app database restore and worker restart; 4 hours including Langfuse analytics restore.

## Restore procedure

1. Stop gateway workers and scheduled sweepers.
2. Restore the app Postgres snapshot or dump into a clean database.
3. Restore the Langfuse Postgres snapshot or dump.
4. Run migrations against the restored app database.
5. Start the gateway with `WORKER_MODE=in_process` or the external worker pool.
6. Verify `/health`, `/ops/slo`, and admin run listing.
7. Resume an interrupted run at an active teacher gate and confirm a new resume job is enqueued.

## Automated drill

`services/gateway/tests/test_checkpoint_recovery.py` simulates the Postgres restore boundary by exporting and restoring run, status-history, active-gate, and job rows, then drives `/teaching-packs/runs/{id}/resume` through FastAPI. The test proves an interrupted run can resume after restored durable state is reloaded.
