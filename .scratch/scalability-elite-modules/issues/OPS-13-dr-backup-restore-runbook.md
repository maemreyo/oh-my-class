# [OPS-13] DR / backup-restore runbook

Status: TODO
Labels: ops, resilience
ADR: 034
Depends on: OPS-05

## Context

State lives in **Postgres** (compose `db` service) — runs, run_jobs, run_events, artifact
snapshots, budget ledgers, notifications, release evidence, and the **LangGraph checkpointer**
(env-mapped to Postgres per ADR-034) — and in **object storage (MinIO)** for exports once OPS-05
lands. There is **no documented backup schedule and no tested restore procedure**. At the
north-star scale, an unrecoverable data loss (or an untested restore that fails when it's finally
needed) would be catastrophic: in-flight runs, checkpoints, teacher artifacts, and audit/privacy
records would be gone. A backup that has never been restored is not a backup.

Critically, DR must cover the **checkpointer and `run_events`** — losing checkpoints means
in-flight runs cannot resume; losing `run_events` means losing the KPI/SLO history and the
audit/data-access trail (PRIV-01).

## Scope

- [ ] **Backup schedule — Postgres**: automated, regular logical/physical backups (including
      WAL/PITR where feasible) covering all gateway tables **and the LangGraph checkpointer
      tables** and **`run_events`**. Define frequency and retention of backups themselves.
- [ ] **Backup schedule — object storage**: backup/replication + lifecycle for the exports bucket
      (OPS-05) so artifacts survive a bucket loss; document versioning/cross-location strategy.
- [ ] **RPO/RTO targets**: define and document Recovery Point Objective (max acceptable data loss)
      and Recovery Time Objective (max acceptable downtime) consistent with the 99.5%
      availability posture, and design the backup cadence to meet the RPO.
- [ ] **Tested restore runbook**: a step-by-step runbook to restore Postgres + object storage from
      backups into a clean environment, including how to bring the checkpointer back so in-flight
      runs can resume (or be safely re-driven via OPS-10/OPS-11). The runbook must be **executed**
      at least once (a real restore drill), not just written.
- [ ] **Restore verification**: after a drill restore, verify integrity — run counts, event
      counts, checkpoint resumability, object-key resolvability, and that a restored run can be
      resumed or replayed without duplicate side effects (rides OPS-10).
- [ ] **Measure achieved RPO/RTO** in the drill and compare against targets; document the gap and
      remediation if targets aren't met.
- [ ] **Schedule/automation home**: model the backup jobs on the existing scheduled cleanup /
      recovery-sweeper pattern (ADR-034 data-lifecycle) so DR jobs run and are monitored like
      other ops jobs; alert (OPS-04) on backup failure.

## Acceptance

- Documented backup schedule covering Postgres (incl. checkpointer + `run_events`) and object
  storage, with backup-retention and RPO/RTO targets stated.
- A **restore drill has been performed** and its runbook validated end-to-end into a clean env.
- Post-restore verification passes: counts match, checkpoints resume, object keys resolve, and a
  restored run replays without duplicate side effects.
- Measured RPO/RTO from the drill are recorded and meet (or have a documented plan to meet) the
  targets.
- Backup-job failure raises an OPS-04 alert.

## References

- `docker-compose*` `db` (Postgres) + MinIO object storage — the stores to protect.
- LangGraph checkpointer (env-mapped to Postgres per ADR-034) — must be in scope for backup +
  restore so in-flight runs resume.
- `services/gateway/models.py` — `RunEvent` and related tables.
- OPS-05 (object-storage exports) — the bucket to back up; hard dependency.
- OPS-10 (idempotency) — restored/resumed runs must not duplicate side effects.
- OPS-04 (alerting) — backup-failure alerts; recovery-sweeper pattern for scheduling.
- ADR-034 decisions 5 and 7.

## Implementation notes

- The single most important deliverable is the **tested** restore — schedule the drill and treat a
  failed/awkward restore as the finding, not an afterthought.
- Checkpointer + `run_events` are easy to forget and the most painful to lose; call them out
  explicitly in both backup and restore steps.
- Coordinate restore correctness with OPS-10: after restore, a partially-completed run must resume
  or replay idempotently, not double-produce exports/events.
- Model backup automation on the existing scheduled-cleanup / recovery-sweeper machinery so it's
  monitored and alertable, not a cron in a corner.
