# [OPS-10] Idempotency / exactly-once hardening

Status: TODO
Labels: ops, resilience
ADR: 034
Depends on: OPS-05

## Context

The queue is a **durable leased job queue** with at-least-once delivery: a worker claims a job
under a lease (`claim_next`, `services/gateway/teaching_pack_job_store.py:91`; `attempts` is
incremented on claim at line 123), and if the lease expires the recovery sweeper resets the job
to `pending` for re-claim (`sweep_stuck_jobs`, `services/gateway/recovery_sweeper.py:33-65`).
LangGraph's checkpointer makes re-entry **resume, not restart**. Request-level idempotency exists
for create/resume via idempotency keys (`services/gateway/teaching_pack_idempotency.py`;
`scoped_*_idempotency_key`; `find_by_idempotency_key`/`get_by_idempotency_key`,
`teaching_pack_job_store.py:67-79`).

The gap is **side-effect idempotency at the tail**. At-least-once + lease re-claim means a job
that dies *after* producing side effects but *before* marking itself complete will be re-run —
and today the side effects are not all proven overwrite-safe/dedup-safe:

- **Exports** are written to the filesystem keyed by `run_id`/`snapshot_id`
  (`FileSystemTeachingPackExportWriter.write_exports`,
  `services/gateway/teaching_pack_export_writer.py:40-70`); OPS-05 moves these to object storage.
  A re-run must overwrite the *same* key deterministically, never append a duplicate artifact.
- **Run events** are appended (`RunEvent`); a re-run could double-emit lifecycle/KPI events,
  corrupting the OPS-03 dashboard counts.
- **Checkpoint-resume** correctness must be asserted, not assumed.

This is about **exactly-once effects**, layered on the existing at-least-once queue — not about
changing the delivery guarantee.

## Scope

- [ ] Formalize **export idempotency**: the object-storage key (OPS-05) is a deterministic
      function of `(run_id, snapshot_id)` (+ format), and `write_exports` performs an
      **overwrite-safe PUT** to that key. Re-running the export for the same approved snapshot set
      produces the identical key set with no duplicates and no orphaned objects.
- [ ] Formalize **event dedup**: give `run_events` a natural dedup key `(run_id, sequence)` (or
      `(run_id, event_type, sequence)`) with a unique constraint, and make emission
      idempotent-upsert / insert-if-absent so a re-run cannot double-count. Add the Alembic
      migration for the unique index (expand-contract; backfill sequence if needed).
- [ ] Verify **checkpoint-resume** semantics: a job that re-enters after a mid-stage kill resumes
      from the last checkpoint rather than redoing completed stages, and completed-stage side
      effects are not re-emitted.
- [ ] Make the completion write **transactional with** the terminal side effects where possible:
      mark job complete + record the export keys/events in one committed unit so a crash leaves a
      consistent "either fully done or fully re-runnable" state (no half-committed tail).
- [ ] Add a **resilience test suite** under `tests/resilience/` (new dir): drive a real run to
      the point of producing exports/events, **kill the worker mid-job**, let the lease expire and
      the sweeper re-claim (or force re-claim), let it run to completion, then assert:
      - NO duplicate export objects/keys in object storage,
      - NO duplicate `run_events` rows for the same `(run_id, sequence)`,
      - NO duplicate artifact snapshots,
      - final run state == the state of an uninterrupted run.

## Acceptance

- The `tests/resilience/` kill-mid-job test passes against a **real DB + real object storage**
  (MinIO) and proves zero duplicate artifacts, exports, or events after re-claim.
- Re-invoking `write_exports` for an unchanged approved set is a no-op-equivalent overwrite:
  same key set, same object count, byte-identical (or content-hash-identical) objects.
- The `(run_id, sequence)` unique constraint rejects a duplicate event insert; emission code
  handles the conflict as idempotent (no crash, no double count).
- A mid-stage kill + resume completes without redoing already-checkpointed stages (asserted via
  stage-entry counts / trace).

## References

- `services/gateway/teaching_pack_job_store.py:91-165` — `claim_next` (attempts++),
  `mark_completed`, `requeue_with_backoff`, `refresh_lease`.
- `services/gateway/recovery_sweeper.py:33-65` — `sweep_stuck_jobs` lease-expiry re-claim.
- `services/gateway/teaching_pack_idempotency.py` — request-level idempotency keys.
- `services/gateway/teaching_pack_export_writer.py:28-70` — export writer Protocol + fs impl.
- `services/gateway/models.py` — `RunEvent`, `Run` tables.
- OPS-05 (object-storage exports) — provides the overwrite-safe key store this builds on.
- ADR-034 decision 7.

## Implementation notes

- Deterministic keys are the crux: never mint a random suffix per attempt. Key = pure function of
  identity `(run_id, snapshot_id, format)`.
- Object-storage overwrite is atomic per-object; prefer a single PUT per key over
  read-modify-write. If a manifest of keys is stored in DB, upsert it under the same transaction
  as job completion.
- `tests/resilience/` should model the failure precisely: kill between "side effect written" and
  "job marked complete", which is exactly the window at-least-once exposes.
- Keep the queue at-least-once — do NOT try to make delivery exactly-once; make *effects*
  idempotent instead.
