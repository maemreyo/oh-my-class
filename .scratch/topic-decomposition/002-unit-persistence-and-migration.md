---
title: Unit persistence — runs table extension and store methods
status: done
labels: [done]
created: 2026-06-30
---

## What to build

Extend run persistence so a parent unit run and its child session runs are first-class rows with parent/child linkage, and so unit status can be **computed** from children without a second source of truth (ADR-017 §Persistence).

Add nullable columns to the existing `runs` table (no new parallel `unit_runs` table — the parent IS a run):

```
runs.parent_run_id   : str | None   # FK → runs.run_id; null for standalone and for the parent
runs.session_id      : str | None   # child only — stable SessionPlan key (e.g. "S01"); part of the unique guard
runs.session_index   : int | None   # child only — order_index for display
runs.unit_role       : Enum("standalone", "unit_parent", "unit_session")  # default "standalone"
runs.lesson_sequence : JSON | None   # parent only — the approved LessonSequence
runs.shared_research : JSON | None   # parent only — UnitContext shared research bundle
runs.persona_snapshot: JSON | None   # parent only — frozen ClassProfile snapshot
```

This slice provides the schema, Alembic migration, and store/query methods only. It must not implement the orchestrator or graph wiring.

## Acceptance criteria

- [x] `services/gateway/models.py` `Run` gains the columns above; `unit_role` defaults to `"standalone"` so existing rows are valid.
- [x] An Alembic migration adds the columns as nullable with safe defaults and is reversible; migration applies cleanly to a real database.
- [x] Store methods exist to: create a child run linked to a parent; list children by `parent_run_id` (indexed); read the parent's `lesson_sequence`; compute unit aggregate status from children (no materialized unit-status column).
- [x] A DB index exists on `parent_run_id`, and a **unique constraint `(parent_run_id, session_id)`** (one child run per session per unit — the orchestrator idempotency guard, issue 010).
- [x] Unit/session lifecycle states (`blocked`, `partially_complete`, `complete`, per-session display) are **computed** from children in the read model — `RunStatus` is **not** extended (no enum migration, no new transitions).
- [x] Single-lesson runs continue to persist and read unchanged (`unit_role="standalone"`, all new columns null).

## Detailed test suite

(Use a real test database — `make migrate` then exercise the real store; no DB mocks per project testing policy.)

- [x] `services/gateway/tests/test_unit_persistence.py`: create a `unit_parent` + 3 `unit_session` children; list-children-by-parent returns exactly the 3, ordered by `session_index`.
- [x] `services/gateway/tests/test_unit_persistence.py`: computed unit status over children states (e.g. 1 complete / 1 generating / 1 failed) returns the expected aggregate counts and `partially_complete`/`complete` resolution.
- [x] `services/gateway/tests/test_unit_persistence.py`: a standalone run round-trips with all new columns null and `unit_role="standalone"`.
- [x] Migration test: apply then downgrade the migration on a real DB; schema returns to baseline and upgrade reapplies cleanly.
- [x] Ran `uv run alembic upgrade head`, `uv run alembic downgrade 013_gate_active_unique && uv run alembic upgrade head`, and `uv run pytest services/gateway/tests/test_unit_persistence.py -q`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
