# Task 10: Queued-Job Alembic Migration

## Status: DONE

## Summary

Added Alembic migration 011 that introduces the `eligible_at` nullable timestamptz column and the composite index `(status, eligible_at)` on `public.run_jobs`. This resolves the task-9 temporary direct-DB-mutation/schema-code mismatch and formalizes the queued backpressure schema in the migration chain.

## Design Decisions

- **No DB enum migration**: `RunJobStatus` is a `StrEnum` mapped to `String(32)` in the ORM (via `Enum(RunJobStatus, native_enum=False)`). No PostgreSQL enum type exists, so no enum migration needed.
- **No `public.RunStatus.QUEUED`**: Per constraint, queueing is job-level only. `RunStatus` is unchanged.
- **Downgrade follows repo convention**: Index dropped before column (correct dependency order for PostgreSQL).
- **Column is nullable**: Existing PENDING jobs have `NULL` eligible_at. Only QUEUED jobs carry a non-NULL value.

## Files Changed

### Production (1 file)

| File | Change |
|------|--------|
| `services/gateway/alembic/versions/011_queued_job_eligible_at.py` | New migration: adds `eligible_at` column + `ix_run_jobs_status_eligible_at` index |

### Tests (1 file, 8 new tests)

| File | New Tests |
|------|-----------|
| `services/gateway/tests/test_migration_011_eligible_at.py` | `test_eligible_at_column_exists_and_is_nullable`, `test_eligible_at_index_exists`, `test_insert_with_null_eligible_at_succeeds`, `test_insert_with_eligible_at_succeeds`, `test_claim_next_ignores_queued_ineligible_job`, `test_claim_next_grabs_eligible_queued_job`, `test_enqueue_pending_with_null_eligible_at`, `test_promote_eligible_uses_indexed_query` |

## Test Results

```
=== New migration tests (8 passed) ===
test_eligible_at_column_exists_and_is_nullable PASSED
test_eligible_at_index_exists PASSED
test_insert_with_null_eligible_at_succeeds PASSED
test_insert_with_eligible_at_succeeds PASSED
test_claim_next_ignores_queued_ineligible_job PASSED
test_claim_next_grabs_eligible_queued_job PASSED
test_enqueue_pending_with_null_eligible_at PASSED
test_promote_eligible_uses_indexed_query PASSED

=== Existing job store tests (16 passed, 0 regressions) ===
test_pipeline_v2_job_store.py: 6 passed
test_pipeline_v2_job_store_leases.py: 10 passed

=== Full gateway suite ===
504 passed, 12 skipped, 0 failed in 13.44s

=== ruff lint ===
All checks passed (0 new violations in task-10 files)
```

## Alembic Verification

### Migration chain

```
010_run_budget_ledgers → 011_queued_job_eligible_at (head)
```

### Upgrade SQL (offline, valid)

```sql
ALTER TABLE public.run_jobs ADD COLUMN eligible_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX ix_run_jobs_status_eligible_at ON public.run_jobs (status, eligible_at);
```

### Downgrade SQL (offline, valid)

```sql
DROP INDEX public.ix_run_jobs_status_eligible_at;
ALTER TABLE public.run_jobs DROP COLUMN eligible_at;
```

### Live DB confirmation

```
Column: ('eligible_at', 'YES', 'timestamp with time zone')
Index: ix_run_jobs_status_eligible_at
```

## Manual QA

- **Enqueue due job**: Created a job with `eligible_at` in the past → `claim_next` immediately claimed it → status changed to RUNNING
- **Enqueue future queued job**: Created a job with `eligible_at` in the future → `claim_next` returned None (job not claimed) → after `promote_eligible`, job moved to PENDING → `claim_next` then claimed it
- **NULL eligible_at**: Standard PENDING jobs have NULL eligible_at → `claim_next` picks them up normally

## Probes

- **ORM-DB alignment**: Migration 011 adds the exact columns/indexes already defined in `pipeline_v2_models.py` RunJob class (task 9). No mismatch remains.
- **No new `public.RunStatus.QUEUED`**: Verified `RunStatus` enum in `models.py` unchanged.
- **No enum type migration**: `RunJobStatus` stored as `String(32)` via `native_enum=False` — no PostgreSQL enum type to migrate.
- **Downgrade safety**: Index dropped before column (PostgreSQL dependency order).
