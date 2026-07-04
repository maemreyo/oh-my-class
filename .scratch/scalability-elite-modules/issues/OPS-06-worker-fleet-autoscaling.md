# [OPS-06] Dedicated worker fleet + queue-depth autoscaling

Status: TODO
Labels: ops, scaling, infra
ADR: 034
Depends on: none

## Context

The worker runs **in-process inside the gateway** today: `lifespan` (`services/gateway/main.py:136`) starts `_run_teaching_pack_worker` as a background task **only when `WORKER_MODE == "in_process"`** (:184, default `in_process` :58). The worker loop calls `run_worker_batch` (`services/gateway/teaching_pack_worker.py:171`) which claims up to `WORKER_CONCURRENCY` jobs (`_worker_runtime_config` :57, capped at `MAX_WORKER_CONCURRENCY = 10` :50) via `TeachingPackJobStore.claim_next` (`with_for_update(skip_locked=True)` — `teaching_pack_job_store.py:113`) and runs each claimed job in a task group.

The queue is already **durable and multi-worker-safe**: `claim_next` uses `SKIP LOCKED` (no double-claim — covered by `test_multi_worker_no_double_claim.py`), leases + heartbeat (`refresh_lease` :167, `_heartbeat` :141), backoff requeue (`requeue_with_backoff` :147), promotion (`promote_eligible` :214), and a recovery sweeper reclaims expired leases (`sweep_stuck_jobs`, `recovery_sweeper.py:33`). So **horizontal scaling is already correct at the data layer** — what's missing is (a) a standalone worker deployable that isn't the API process, and (b) autoscaling that deployable on queue depth.

Per ADR-034 §4: a dedicated worker deployable (`WORKER_MODE != in_process`), **autoscaled on pending `run_jobs` count**, ceilinged by provider rate limits (ties to OPS-01's per-provider breaker), keeping in-process for dev. This is the throughput lever for 5,000 packs/day at p95 < 8 min.

## Scope

- [ ] **Standalone worker entrypoint** — a process/module that runs the `run_worker_batch` loop (the body of `_run_teaching_pack_worker` :118-125: claim batch, sleep `idle_sleep_seconds` when empty) **without** starting the FastAPI app. It builds the same graph/checkpointer/store/executor (`build_teaching_pack_graph`, `get_checkpointer(env)`, env-mapped store per `main.py:167-172`) and the same `TeachingPackWorkerConfig` (worker_id, `lease_seconds=120`, concurrency). Distinct `worker_id` per replica (e.g. hostname/pod name) so leases and heartbeats are per-replica.
- [ ] **Gate on `WORKER_MODE`** — when `WORKER_MODE != "in_process"`, the gateway must NOT start the in-process worker (already the case — :184 only starts it for `in_process`). The dedicated entrypoint runs the worker; the API runs API-only. Keep the recovery sweeper decision explicit: it currently runs in the API lifespan (`_run_teaching_pack_sweeper` :182 always) — decide whether the sweeper lives with API or workers (recommend: exactly one sweeper owner; document it) so leases are reclaimed regardless of worker topology.
- [ ] **Container/deployable** — a worker image + deployment manifest (K8s Deployment or compose service) running the entrypoint, sharing DATABASE_URL / REDIS_URL / LLM env with the API. Separate from the API deployment so the two scale independently.
- [ ] **Queue-depth autoscaling** — autoscale worker replicas on the count of claimable jobs: `RunJob.status IN (PENDING, QUEUED-and-eligible)`. Use KEDA (Postgres scaler on that count) or an HPA driven by a queue-depth metric exported from OPS-03. Scale-up on backlog, scale-down to a floor when drained. There is already an index to make the count cheap: `ix_run_jobs_status_created_at (status, created_at)` (`teaching_pack_models.py:231`).
- [ ] **Provider-rate-limit ceiling** — cap max replicas × per-replica concurrency so aggregate LLM demand stays under the provider rate limit; when a provider breaker is open (OPS-01), autoscaling must not keep scaling up into a dead provider (respect the breaker / backpressure signal). The autoscale ceiling is the throughput safety valve.
- [ ] **Keep in-process for dev** — `WORKER_MODE=in_process` (default) unchanged: single-process dev with the worker in the API lifespan, no separate deployable, no autoscaler.
- [ ] **Graceful lifecycle** — the standalone worker must stop claiming and finish/checkpoint in-flight jobs on shutdown (SIGTERM), releasing leases — full drain behavior is specified in OPS-08; here, ensure the entrypoint's loop is structured so OPS-08 can hook drain (breakable claim loop, releasable leases). Note the dependency direction (OPS-08 depends on OPS-06).

## Acceptance

- With `WORKER_MODE=external` (or any non-`in_process`), the gateway serves API only and starts no in-process worker; a separate worker process claims and runs jobs against the same Postgres queue.
- Running ≥2 worker replicas processes the queue with **no double-claim** (relies on existing `SKIP LOCKED`; assert via the existing multi-worker test extended to the standalone entrypoint) and correct lease/heartbeat behavior.
- Autoscaling scales worker replicas up as pending `run_jobs` grows and back down to the floor when the queue drains, capped at the configured ceiling; scaling does not exceed the provider rate-limit ceiling and backs off when a provider breaker is open.
- Under a 5,000-pack/day-equivalent load (QA-02), p95 pack stays < 8 min with autoscaling engaged.
- Dev (`WORKER_MODE=in_process`) is unchanged and needs no autoscaler.
- Exactly one recovery-sweeper owner exists regardless of worker count (no duplicate or zero sweepers).

## References

- `services/gateway/main.py` — `_worker_runtime_config` :57 (`WORKER_MODE` :58 default `in_process`, `WORKER_CONCURRENCY` :59, `MAX_WORKER_CONCURRENCY=10` :50), `_run_teaching_pack_worker` :83 (loop :118-125, `executor_factory` :94, `TeachingPackWorkerConfig` :111), `_run_teaching_pack_sweeper` :70 (60s), lifespan worker start gate :184, env-mapped store :167-172, `build_teaching_pack_graph` :175, `get_checkpointer(environment)` :163.
- `services/gateway/teaching_pack_worker.py` — `run_worker_batch` :171 (claim up to `worker_concurrency`, `SKIP LOCKED` via `claim_next`), `_run_claimed_job` :192, `_heartbeat` :141, `_heartbeat_interval` :165.
- `services/gateway/teaching_pack_job_store.py` — `claim_next` :91 (`with_for_update(skip_locked=True)` :113), `refresh_lease` :167, `requeue_with_backoff` :147, `promote_eligible` :214.
- `services/gateway/teaching_pack_models.py:231` — `ix_run_jobs_status_created_at` (cheap queue-depth count).
- `services/gateway/recovery_sweeper.py` — `sweep_stuck_jobs` :33 (lease reclamation — the single-owner question).
- Tests: `services/gateway/tests/test_multi_worker_no_double_claim.py`, `test_worker_concurrency.py`, `test_lease_heartbeat.py`.
- `packages/agents/checkpointer.py` (env-mapped checkpointer the worker must build).
- ADR-034 §4 (dedicated worker deployable, autoscale on queue depth, ceiling at provider rate limit, in-process for dev).

## Implementation notes

- The standalone entrypoint is largely a **re-host of existing code**, not new logic: it constructs the same graph/store/checkpointer/executor as `lifespan` and runs the same `run_worker_batch` loop. Factor the executor/graph construction out of `lifespan` into a shared builder so API and worker use one code path (avoids drift).
- Queue-depth for autoscaling = claimable jobs. Prefer a metric the autoscaler can read directly: KEDA's Postgres scaler can run `SELECT count(*) FROM run_jobs WHERE status='pending' OR (status='queued' AND eligible_at <= now())`. Reuse `_queue_depth_by_teacher`'s predicate shape (`slo_metrics.py:111`) for consistency but as a global count.
- Ceiling math: `max_replicas * WORKER_CONCURRENCY` must stay ≤ provider concurrent-request budget. Since cost is not a constraint but provider rate limits are, this ceiling — not cost — is the real cap. Document the number and tie it to the OPS-01 fallback provider's headroom.
- Distinct `worker_id` per replica is essential: `claim_next`/`refresh_lease` key leases on `lease_owner`; two replicas sharing `"gateway-worker"` would corrupt heartbeat semantics. Use pod name / hostname.
- Decide the sweeper owner now: simplest is to keep it in the API lifespan (one API-side sweeper), independent of worker count — but then API must always be up for lease reclamation. Alternatively run it as a singleton worker job. Pick one and state it; OPS-04's "queue not draining" page depends on the sweeper actually running.
- This unblocks OPS-08 (drain on SIGTERM) — keep the claim loop cleanly interruptible (check a shutdown flag before each `claim_next` batch).
