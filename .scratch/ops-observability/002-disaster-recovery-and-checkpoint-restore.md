---
title: Disaster recovery — backup/restore + LangGraph checkpoint recovery
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

A backup/restore strategy and a tested recovery path for the durable state. Redis is ephemeral (noeviction, no persistence) and needs no backup; the critical state is Postgres.

- **Backup**: scheduled `pg_dump` (or managed snapshots) of the app DB — runs, **LangGraph checkpoints**, `class_profiles`, outcome store — plus Langfuse DB; documented cadence + retention + offsite.
- **Restore drill**: a documented + tested restore procedure, including **checkpoint recovery** — an interrupted run (paused at a teacher gate) must resume correctly after a restore.
- **RPO/RTO** targets documented.

## Acceptance criteria

- [ ] Scheduled backups cover the app DB (runs, checkpoints, class_profiles, outcomes) and Langfuse; cadence/retention/offsite documented.
- [ ] A restore procedure is documented with RPO/RTO targets.
- [ ] A restore drill is automated/tested: an interrupted run resumes from its checkpoint after restore.
- [ ] Redis is confirmed safe to lose (ephemeral) — no backup required, documented.

## Detailed test suite

(Real DB; real checkpointer.)

- [ ] `services/gateway/tests/test_checkpoint_recovery.py`: a run interrupted at a gate, after a DB restore (or checkpointer reload), resumes via `/teaching-packs/runs/{id}/resume` and completes.
- [ ] Backup/restore drill test: dump → drop → restore → run history + pending gates intact.
- [ ] Run `uv run pytest services/gateway/tests/test_checkpoint_recovery.py -v`.

## Blocked by

None - can start immediately
