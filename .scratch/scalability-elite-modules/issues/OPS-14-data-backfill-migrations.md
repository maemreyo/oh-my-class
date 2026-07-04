# [OPS-14] Data backfill migrations

Status: TODO
Labels: ops, migration
ADR: 034
Depends on: OPS-05, OPS-09

## Context

Two structural changes in this workstream require **one-time backfills** of existing data, and
both must be **expand-contract safe** so they can run against a live system with zero downtime
(ADR-034 decision 8):

1. **`org_id` (OPS-09)**: the new tenancy layer adds an additive, initially-nullable `org_id` FK
   to `runs` (and `run_jobs`). Historical rows have no `org_id`. Before the contract migration can
   enforce NOT NULL + FK + RLS, every existing row must be backfilled with the correct org derived
   from its `teacher_id` (via the teacher→org membership introduced in OPS-09).

2. **Exports fs → object storage (OPS-05)**: existing exports live on the local filesystem under
   `.scratch/pipeline-v2/artifacts/exports/<run_id>/...`
   (`FileSystemTeachingPackExportWriter.base_dir`,
   `services/gateway/teaching_pack_export_writer.py:40-41`), with DB references that may be paths.
   OPS-05 moves exports to object storage keyed by `(run_id, snapshot_id)` and stores **keys, not
   paths**, in the DB. Existing exports must be migrated: upload each file to its deterministic
   object key and rewrite the DB reference from path → key.

Without these backfills, OPS-09's NOT-NULL/RLS enforcement can't turn on, and old exports become
unreachable after the storage cutover.

## Scope

- [ ] **`org_id` backfill**: a one-time, idempotent, batched backfill that sets `runs.org_id`
      (and `run_jobs.org_id`) from each row's `teacher_id` → org membership (OPS-09). Handle
      teachers with no org per the OPS-09 policy (default personal org vs flagged for review) — do
      not leave rows null if the plan is to enforce NOT NULL.
- [ ] **Expand-contract sequencing for `org_id`**: (expand) OPS-09 adds nullable column →
      (backfill) this issue populates it → (contract) a later migration adds NOT NULL + FK +
      enables RLS. Ship the contract migration only after the backfill verifies 100% coverage.
- [ ] **Exports backfill**: a one-time, idempotent, batched job that, for each existing export
      file under the fs base dir, computes its deterministic object key `(run_id, snapshot_id)`
      (matching OPS-05/OPS-10 keying), uploads it (overwrite-safe), and rewrites the DB reference
      from path → key. Verify each uploaded object is resolvable before rewriting the reference;
      leave the fs copy until verified.
- [ ] **Idempotency + resumability**: both backfills must be safe to re-run (skip already-migrated
      rows/objects) and resumable after interruption — they operate on production-scale data.
- [ ] **Verification queries**: post-backfill checks — `org_id` coverage == 100% (no nulls where
      NOT NULL will land); every export DB reference resolves to an existing object key; no
      dangling fs-only exports for live runs.
- [ ] **Rollback/safety**: keep the fs export copies until object-storage verification passes;
      make the `org_id` backfill reversible (or at least the NOT-NULL contract migration
      gated/reversible) if coverage checks fail.
- [ ] **Run mechanics**: deliver as Alembic data migrations and/or standalone runnable scripts
      (whichever fits the expand-contract flow), following the existing migrations layout
      (`services/gateway/alembic/versions/`, next ids after `020_*` from OPS-09).

## Acceptance

- After the `org_id` backfill, 100% of existing `runs`/`run_jobs` rows have a correct `org_id`
  (verification query returns zero nulls), enabling the OPS-09 NOT-NULL/RLS contract migration.
- After the exports backfill, every existing export has a resolvable object-storage key and its DB
  reference is a key (not a path); no live run points only at fs.
- Both backfills are idempotent and resumable — re-running or resuming after a kill produces the
  same end state with no duplicate uploads/rows.
- Verification queries pass; the contract migrations run clean.
- fs export copies are retained until object-storage verification succeeds.

## References

- `services/gateway/teaching_pack_export_writer.py:40-41` — fs export `base_dir`
  (`.scratch/pipeline-v2/artifacts/exports`).
- `services/gateway/models.py:75-103` — `runs` table (target of `org_id` backfill).
- `services/gateway/alembic/versions/` — migrations layout + latest id (`019_*`; OPS-09 adds
  `020_*`).
- OPS-05 (object storage + deterministic keys) — target store + keying.
- OPS-09 (org layer + teacher→org membership) — source of `org_id`; provides the nullable column.
- OPS-10 (idempotency/deterministic keys) — same key function used by the exports backfill.
- ADR-034 decisions 3, 6, 8.

## Implementation notes

- Batched + idempotent is mandatory — these run over production-scale data and must survive a
  restart without double-uploading or re-touching migrated rows (use a done-marker / skip
  already-keyed rows).
- The exports backfill MUST use the same deterministic key function as OPS-05/OPS-10 so migrated
  objects land where the live writer expects them — otherwise re-runs would create duplicates.
- Never enable OPS-09 NOT-NULL/RLS before the `org_id` coverage check is green; gate the contract
  migration on the verification query.
- Keep fs copies as the rollback path for the storage cutover until verification passes; only then
  schedule fs cleanup (OPS-07 lifecycle).
