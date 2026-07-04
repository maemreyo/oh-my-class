# [OPS-08] Zero-downtime deploys — worker drain on SIGTERM, expand-contract migrations, feature flags, API connection draining

Status: TODO
Labels: ops, deploy, reliability
ADR: 034
Depends on: OPS-06

## Context

At the mid-scale target with a dedicated, autoscaled worker fleet (OPS-06) and a 99.5% success SLO, **deploys must not fail in-flight runs**. Per ADR-034 §8: worker **drain on SIGTERM** (stop claiming, checkpoint/finish, release leases), **expand-contract Alembic migrations**, **feature flags** for staged rollout/rollback, and **API connection draining**.

The mechanics that make zero-downtime *possible* already exist:
- **Durable leased queue**: a job in-flight is a `RunJob` with a lease (`lease_owner`/`lease_expires_at`). If a worker dies mid-job, the recovery sweeper reclaims it (`sweep_stuck_jobs` — resets to `PENDING` if `attempts < max`, `recovery_sweeper.py:33`). So a hard kill is *survivable* — but it wastes the in-flight work and costs latency. Drain makes shutdown *clean*: release the lease so another worker re-claims immediately, or finish the job.
- **Checkpointer**: LangGraph state is checkpointed (`packages/agents/checkpointer.py`, env-mapped MemorySaver/Sqlite/Postgres; prod PostgresSaver via `get_checkpointer(environment)` at `main.py:163`), so a run can resume from its last checkpoint after a worker restart.
- **Lease/backoff/requeue primitives**: `requeue_with_backoff` :147, `refresh_lease` :167, `promote_eligible` :214, `claim_next` (`SKIP LOCKED`) :113 — all the pieces to hand a job off cleanly.
- **Migrations**: Alembic is in place (`scripts/run_migrations.sh` → `alembic upgrade head`, `make migrate`; versions under `services/gateway/alembic/versions/` up to `019_*`).

The gap is the **deploy discipline** that uses these: a SIGTERM handler that drains, a migration convention that never breaks the running old version, feature-flagged rollout, and API connection draining. This depends on OPS-06's standalone worker entrypoint (the thing that receives SIGTERM).

## Scope

- [ ] **Worker drain on SIGTERM** — the standalone worker (OPS-06 entrypoint) installs a SIGTERM handler that: (1) **stops claiming** new jobs (breaks the `run_worker_batch` loop before the next `claim_next`), (2) lets in-flight jobs **finish or checkpoint** within a bounded grace period, (3) **releases leases** for anything not finished (clear `lease_owner`/`lease_expires_at` or requeue) so another replica re-claims immediately instead of waiting for lease expiry. Use the existing lease primitives; do not invent a new state. Bound the grace period; after it, rely on the sweeper as the safety net (a drained-but-unfinished job must be left in a re-claimable state, never lost).
- [ ] **Grace-period sizing** — the SIGTERM→SIGKILL grace (K8s `terminationGracePeriodSeconds` / compose stop timeout) must accommodate finishing a typical stage or cleanly checkpointing; document the value against `lease_seconds=120` and p95 stage latency (OPS-02). A drain that's shorter than a stage should checkpoint+release, not block.
- [ ] **Expand-contract Alembic migrations** — adopt and document the expand-contract convention so a migration is always compatible with the *currently running* app version:
  - Expand phase: additive only (new nullable columns, new tables, new indexes `CONCURRENTLY`) — safe to run before new code ships.
  - Contract phase: remove/rename only after all instances run the new code — a separate later migration.
  - No destructive change in the same migration as the code that needs it. Backfills (OPS-14) run between expand and contract.
- [ ] **Feature flags for staged rollout/rollback** — a feature-flag mechanism to gate new behavior (e.g. object-storage writer OPS-05, breaker→backpressure coupling OPS-01) so a deploy can roll out staged and roll back **without a redeploy**. Flags env/config-driven, read at the decision point, default-safe.
- [ ] **API connection draining** — on API shutdown, stop accepting new connections, let in-flight HTTP/SSE requests complete within a grace period, then exit. SSE streams (`teaching_pack_stream.py`) need explicit handling: signal stream end cleanly rather than dropping the socket. Wire into the FastAPI `lifespan` shutdown (`main.py:186-192` `finally`).
- [ ] **Env mapping** — dev: drain/flags present but trivial (in-process worker, single instance); no rolling deploy. staging/prod: full drain + expand-contract enforced + flags + connection draining; deploys are rolling with the old version staying healthy throughout.

## Acceptance

- Sending SIGTERM to a busy worker: it stops claiming, finishes or checkpoints in-flight jobs within the grace period, releases leases, and exits cleanly — **no job is lost and none fails** solely due to the deploy; a peer worker re-claims released jobs immediately (not after a 120s lease timeout).
- A rolling deploy (old + new instances briefly coexisting) with an expand-phase migration applied causes **no errors** in the still-running old version.
- A new behavior can be toggled on/off via feature flag without redeploying; rollback is a flag flip.
- API shutdown drains in-flight requests/SSE streams within the grace period instead of dropping them.
- Across a full staging rolling deploy under load (QA-02), measured run-success stays ≥ 99.5% and no run is failed by the deploy.
- Dev single-instance flow is unaffected.

## References

- OPS-06 — standalone worker entrypoint (SIGTERM target; interruptible claim loop).
- `services/gateway/teaching_pack_worker.py` — `run_worker_batch` :171 (loop to make drainable), `_heartbeat` :141, `refresh_lease` usage :148.
- `services/gateway/teaching_pack_job_store.py` — lease primitives for clean handoff: `requeue_with_backoff` :147, `refresh_lease` :167, `claim_next` :91 (`SKIP LOCKED` :113), `promote_eligible` :214, `mark_completed`/`mark_failed` :127/:137.
- `services/gateway/recovery_sweeper.py:33` — `sweep_stuck_jobs` (safety net for anything not cleanly released; `DEFAULT_MAX_ATTEMPTS=3` :28).
- `packages/agents/checkpointer.py` + `services/gateway/main.py:163` — `get_checkpointer(environment)` (resume-from-checkpoint enabler; prod PostgresSaver).
- `services/gateway/main.py:136-192` — `lifespan` (shutdown `finally` :188, `task_group.cancel_scope.cancel()` :189, engine dispose :191) — where API drain hooks.
- `services/gateway/teaching_pack_stream.py` — SSE streams needing clean close on drain.
- `scripts/run_migrations.sh` (`alembic upgrade head`), `make migrate`, `services/gateway/alembic/versions/` (latest `019_*`) — migration surface for expand-contract.
- ADR-034 §8 (worker drain, expand-contract migrations, feature flags, API connection draining).

## Implementation notes

- **Reuse, don't reinvent, the lease handoff.** Clean drain = release the lease (or `requeue_with_backoff` with `eligible_at=now`) so `claim_next`'s `SKIP LOCKED` immediately gives the job to a peer. The sweeper already handles the *un*clean case; drain just makes the common case fast. Do not add a new "draining" job status if releasing the lease suffices.
- The claim loop must check a shutdown flag *before* each batch (`run_worker_batch` call in `_run_teaching_pack_worker` :118), so SIGTERM stops new claims immediately while letting the current batch's task group finish or checkpoint. anyio task groups + the existing `cancel_scope` give a clean cancellation seam.
- Expand-contract is a **convention + checklist**, largely docs + a migration-authoring guideline, plus possibly a CI check that a single migration isn't both additive and destructive. Reference it from the migrations README. `CREATE INDEX CONCURRENTLY` can't run in a transaction — note the Alembic caveat.
- Feature flags: keep it minimal (env/config-backed boolean registry read at decision points), not a flag SaaS. The flags that matter first are the ones gating OPS-01/OPS-05 cutover so those can dark-launch and roll back. Default-safe = flag off preserves current behavior.
- SSE drain: on shutdown, push a terminal event to open streams (the event bus already has terminal-event semantics — `_TERMINAL_EVENTS`, `packages/agents/events.py:67`) and close, rather than letting clients hang on a dropped socket.
- Grace period must exceed clean-checkpoint time but need not exceed a full stage — checkpoint+release is the fallback for jobs that can't finish in time; the checkpointer + sweeper make that safe.
- Tie the deploy story together: expand migration → deploy new code behind flags → drain old workers (they release leases, new workers pick up) → enable flags staged → contract migration later. Document this runbook (feeds OPS-13 DR runbook).
