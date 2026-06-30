---
title: Scalable worker pool, intra-worker concurrency, and lease heartbeat
status: done
labels: []
created: 2026-06-30
---

## What to build

Lift the throughput ceiling and fix a latent double-execution bug in the teaching-pack worker. Today `main.py` runs a single in-process `_run_teaching_pack_worker` whose `run_one()` claims **one job at a time** with a **fixed 120s lease and no heartbeat**; `TeachingPackJobStore` already uses `SELECT … FOR UPDATE SKIP LOCKED` (multi-worker-safe), and gate interrupts do **not** pin workers (resume is a separate `TeachingPackResumeJob`).

- **Topology**: a `WORKER_MODE` config — `in_process` (dev, current behavior) vs `external` (prod: a separate, horizontally-scalable worker deployment). Same `TeachingPackWorker`/`JobStore`; only the process boundary changes.
- **Intra-worker concurrency**: replace the one-job-at-a-time loop with a bounded async pool (`worker_concurrency=K`, semaphore) since jobs are LLM-I/O-bound; total throughput = `workers × K`. Safe because gates release the worker (resume = new job).
- **Lease heartbeat (correctness fix)**: refresh the lease periodically (~lease/3) while a job runs `ainvoke`, so a stage longer than the lease is not reclaimed mid-run. Add **idempotent stage re-execution** as defense-in-depth using the existing `completed_stages` (skip already-completed stages on re-claim).

## Acceptance criteria

- [x] `WORKER_MODE` selects in-process (dev) vs external (prod) worker; both use the same `JobStore` claim/lease path.
- [x] A worker runs up to `worker_concurrency` jobs concurrently (bounded semaphore); idle backoff preserved.
- [x] Running jobs heartbeat-refresh their lease; a stage exceeding the base lease is **not** reclaimed while its worker is alive.
- [x] Re-claiming a partially-completed job skips `completed_stages` (no duplicate side effects / double export).
- [x] Multiple workers (external mode) process disjoint jobs with no double-claim (`SKIP LOCKED` verified).
- [x] Gate interrupts still release the worker (resume remains a separate job).

## Detailed test suite

(Real Postgres job store; real worker.)

- [x] `services/gateway/tests/test_worker_concurrency.py`: with `worker_concurrency=4`, four eligible jobs run concurrently; a fifth waits.
- [x] `services/gateway/tests/test_lease_heartbeat.py`: a job whose stage runs > base lease keeps its lease (heartbeat) and is not reclaimed by the sweeper; killing the worker lets the sweeper reclaim it.
- [x] `services/gateway/tests/test_idempotent_reclaim.py`: a reclaimed job resumes from `completed_stages` and does not re-run completed stages (no duplicate artifacts/exports).
- [x] `services/gateway/tests/test_multi_worker_no_double_claim.py`: two workers against one queue never claim the same job.
- [x] Run `uv run pytest services/gateway/tests/test_worker_concurrency.py services/gateway/tests/test_lease_heartbeat.py services/gateway/tests/test_idempotent_reclaim.py services/gateway/tests/test_multi_worker_no_double_claim.py -v`.

## Verification

- `uv run pytest services/gateway/tests/test_worker_concurrency.py services/gateway/tests/test_lease_heartbeat.py services/gateway/tests/test_idempotent_reclaim.py services/gateway/tests/test_multi_worker_no_double_claim.py services/gateway/tests/test_worker_runtime_config.py -q` → 8 passed.
- LSP diagnostics clean for `services/gateway/teaching_pack_worker.py`, `services/gateway/teaching_pack_job_store.py`.

## Blocked by

None - can start immediately
