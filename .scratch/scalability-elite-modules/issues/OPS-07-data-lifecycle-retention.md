# [OPS-07] Data lifecycle & retention — revision-window-aware pruning, event partitioning + KPI rollup, object-storage lifecycle

Status: TODO
Labels: ops, storage, data-governance
ADR: 034
Depends on: OPS-05

## Context

At 5,000 packs/day the DB and object store grow without bound unless data is pruned. Per ADR-034 §5, retention/TTL must be **revision-window-aware** (never prune data a teacher can still act on), `run_events` should be **time-partitioned with a KPI rollup before prune**, object-storage should have **lifecycle rules**, and cleanup should be a **scheduled job modeled on the recovery sweeper**.

Existing building blocks (build additively — do not rebuild):
- **Retention config** exists: `services/gateway/retention.py` (`RetentionConfig` :27 — `run_metadata=365`, `student_evidence=30`, `artifacts=180`, `events=90`, `snapshots=180`, `class_profiles=365` days; `is_expired(deleted_at, retention_days)` :75). Soft-delete is modeled: `Run.deleted_at` (`models.py:107`) and `SloSnapshot` already filters `deleted_at.is_(None)`.
- **Purge logic** exists for student evidence: `services/gateway/purge.py` (`purge_student_evidence` :79, cutoff by `student_evidence` retention :90, strips `student_evidence` from `class_info` :110) — the pattern to generalize.
- **Recovery sweeper** is the scheduling model: `_run_teaching_pack_sweeper` (60s loop, `services/gateway/main.py:70`) calling `sweep_stuck_jobs`/`sweep_escalated_gates` (`recovery_sweeper.py`).
- **Object storage** for exports arrives in **OPS-05** (keys namespaced `exports/<run_id>/...`) — lifecycle rules target those.

The **critical safety invariant** (ADR-034 §5): pruning must **never** touch a run that is pending, escalated, or **within its revision window**. ADR-026 (`docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`) defines a `request_revision` / revert window: a fast-lane auto-approval is **revertible** until downstream `export_finalize` materializes, and teachers can request revisions. Pruning a run inside that window would destroy data a teacher is entitled to revise. Fail-closed: if we cannot prove a run is outside every protective window, do not prune it.

## Scope

- [ ] **Revision-window-aware prune predicate** — a pure predicate deciding whether a run/artifact is prunable: prunable **only if** terminal AND soft-deleted-past-retention AND NOT pending/escalated AND NOT within the ADR-026 revision/revert window. Reuse `is_expired` (`retention.py:75`) for the retention part; add the window checks. Default deny (fail-closed) on any ambiguity. This is the safety core of the issue.
- [ ] **Generalize purge beyond student_evidence** — extend the `purge.py` pattern to prune each data class per `RetentionConfig` (artifacts, events, snapshots, run_metadata, class_profiles), each gated by the revision-window-aware predicate. Keep `student_evidence`'s tighter 30-day rule (privacy-by-design, ADR-034 §10) — it may be purged *from active runs* independently of run-level pruning, as `purge_student_evidence` already does.
- [ ] **`run_events` time-partitioning** — partition `RunEvent` (`teaching_pack_models.py:204`) by time (monthly range partitions on `created_at`) so old event partitions can be dropped cheaply instead of row-by-row deletes at 5,000 packs/day volume. Additive, expand-first migration (OPS-08 expand-contract discipline).
- [ ] **KPI rollup before prune** — before dropping/pruning an events partition, roll its KPIs up into a summary table (daily aggregates feeding OPS-03: success rate, p95, escalate count, healing distribution, breaker trips, tokens) so historical KPIs survive event deletion. OPS-03 dashboards must read live events + rolled-up history seamlessly.
- [ ] **Object-storage lifecycle rules** — configure S3/MinIO lifecycle rules on the OPS-05 exports bucket (expire/transition objects under `exports/<run_id>/` past retention), aligned with the DB `artifacts`/`snapshots` retention so DB keys and objects expire consistently. Never expire an object whose run is still within a protective window.
- [ ] **Scheduled cleanup job** — a periodic cleanup modeled on the recovery sweeper (its own slower cadence, e.g. daily, not the 60s sweep), running the prune predicate + partition drop + rollup. Idempotent and interruptible. Decide its owner (API sweeper vs a scheduled worker job — consistent with OPS-06's sweeper-owner decision).
- [ ] **Env mapping** — dev: retention loose/effectively off (don't prune local dev data), cleanup job may run in dry-run/log-only mode. staging/prod: retention enforced, partitions dropped, lifecycle rules active, rollup populated.

## Acceptance

- No run that is pending, escalated, or within its ADR-026 revision/revert window is ever pruned — proven by a test that constructs runs in each protected state and asserts the prune predicate returns "keep" (fail-closed on ambiguity).
- Data past its retention window (per `RetentionConfig`) and outside all protective windows is pruned: DB rows removed and corresponding S3 objects expired by lifecycle rule.
- `run_events` is time-partitioned; an old partition can be dropped after its KPIs are rolled up, and OPS-03 dashboards show continuous history across the live/rolled-up boundary.
- `student_evidence` still purged at 30 days from active runs (privacy), independent of run-level pruning.
- Dev does not prune local data; cleanup runs dry-run in dev.
- Verified against real Postgres (real partitioning + real prune) and real MinIO lifecycle (real object expiry via OPS-05's bucket), no mocks.

## References

- `services/gateway/retention.py` — `RetentionConfig` :27, `_DEFAULT_RETENTION` :17 (`student_evidence=30`, `events=90`, etc.), `is_expired` :75, `retention_days_for_class_info` :69.
- `services/gateway/purge.py` — `purge_student_evidence` :79 (pattern to generalize; cutoff :90, strip :110).
- `services/gateway/models.py` — `Run.deleted_at` :107, `Run.updated_at` :104, `cost_usd` :102 (soft-delete + terminal signals).
- `services/gateway/recovery_sweeper.py` + `services/gateway/main.py:70` (`_run_teaching_pack_sweeper`) — scheduling model.
- `services/gateway/teaching_pack_models.py:204` — `RunEvent` (partition target), `created_at` :224.
- `services/gateway/slo_metrics.py:54` — already filters `Run.deleted_at.is_(None)` (rollup must match this terminal/soft-delete semantics).
- ADR-026 (`docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`) — revision/revert window (`request_revision`, revert before `export_finalize`); ADR-034 §5, §10.
- OPS-05 (object keys `exports/<run_id>/...` — lifecycle target); OPS-03 (KPI rollup consumer); OPS-08 (expand-contract migrations).

## Implementation notes

- **The prune predicate is the whole safety story** — make it a pure, exhaustively table-tested function: `is_prunable(run, artifacts, now) -> bool`, default `False`. Every protective condition (pending, escalated, revision-window-open, revert-window-open, retention-not-elapsed) is an explicit deny clause. Enumerate ADR-026's window states precisely (auto-approved-but-not-finalized is protected; revision-requested is protected).
- Reuse `is_expired` for the retention arithmetic so there's one definition of "past retention".
- Partitioning: Postgres declarative range partitioning on `run_events(created_at)`; the migration must be expand-first (create partitioned structure, migrate/attach, then switch writes) to satisfy OPS-08. Dropping a partition is O(1) vs mass `DELETE`.
- KPI rollup schema should be the same shape OPS-03's views produce, so the dashboard `UNION`s live-view + rollup-table without special-casing. Roll up *before* the partition is dropped, in the same transaction/step, and verify the rollup exists before drop (fail-closed: never drop un-rolled-up data).
- Align object lifecycle TTL with DB `artifacts`/`snapshots` retention (180 days default) so a signed-URL fetch never resolves to an object that outlived its DB key or vice versa.
- Cleanup cadence: daily is plenty; run it off-peak. Keep it interruptible and idempotent (re-running mid-way is safe) so OPS-08 drain doesn't corrupt a partial prune.
- Coordinate the sweeper/cleanup owner with OPS-06 — don't run two cleanup jobs across a worker fleet.
