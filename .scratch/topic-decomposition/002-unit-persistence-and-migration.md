---
title: Unit persistence — runs table extension and store methods
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Extend run persistence so a parent unit run and its child session runs are first-class rows with parent/child linkage, and so unit status can be **computed** from children without a second source of truth (ADR-017 §Persistence).

Add nullable columns to the existing `runs` table (no new parallel `unit_runs` table — the parent IS a run):

```
runs.parent_run_id   : str | None   # FK → runs.run_id; null for standalone and for the parent
runs.session_index   : int | None
runs.unit_role       : Enum("standalone", "unit_parent", "unit_session")  # default "standalone"
runs.lesson_sequence : JSON | None   # parent only — the approved LessonSequence
runs.shared_research : JSON | None   # parent only — UnitContext shared research bundle
runs.persona_snapshot: JSON | None   # parent only — frozen ClassProfile snapshot
```

This slice provides the schema, Alembic migration, and store/query methods only. It must not implement the orchestrator or graph wiring.

## Acceptance criteria

- [ ] `services/gateway/models.py` `Run` gains the columns above; `unit_role` defaults to `"standalone"` so existing rows are valid.
- [ ] An Alembic migration adds the columns as nullable with safe defaults and is reversible; `make migrate` applies cleanly to a real database.
- [ ] Store methods exist to: create a child run linked to a parent; list children by `parent_run_id` (indexed); read the parent's `lesson_sequence`; compute unit aggregate status from children (no materialized unit-status column).
- [ ] A DB index exists on `parent_run_id`.
- [ ] Single-lesson runs continue to persist and read unchanged (`unit_role="standalone"`, all new columns null).

## Detailed test suite

(Use a real test database — `make migrate` then exercise the real store; no DB mocks per project testing policy.)

- [ ] `services/gateway/tests/test_unit_persistence.py`: create a `unit_parent` + 3 `unit_session` children; list-children-by-parent returns exactly the 3, ordered by `session_index`.
- [ ] `services/gateway/tests/test_unit_persistence.py`: computed unit status over children states (e.g. 1 approved / 1 generating / 1 failed) returns the expected aggregate counts and `partially_complete`/`complete` resolution.
- [ ] `services/gateway/tests/test_unit_persistence.py`: a standalone run round-trips with all new columns null and `unit_role="standalone"`.
- [ ] Migration test: apply then downgrade the migration on a real DB; schema returns to baseline and existing run rows survive upgrade.
- [ ] Run `make migrate` and `uv run pytest services/gateway/tests/test_unit_persistence.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
