---
title: Teacher content lifecycle — library, fork/re-edit, portability
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Give the teacher a first-class content lifecycle beyond the thin `GET /run` list.

- **Library**: browse/search/filter packs and units by class (ClassProfile), subject, grade, topic, status. Reuse run/artifact storage + unit aggregation + the existing admin run-filters; organize around the class.
- **Fork / re-edit / variant**: re-open a past pack, edit the blueprint, and regenerate as a **new run linked to the source** (`forked_from_run_id` — generalize the existing `parent_run_id` lineage); the original is **immutable** (history preserved). Supports difficulty/methodology variants from an approved pack.
- **Data portability (PDPD/GDPR)**: an export-my-data endpoint bundling the teacher's runs/artifacts/class-profiles/outcomes in a portable format; account erasure cascades (ties to retention/purge + effectiveness-loop consent).

## Acceptance criteria

- [ ] A library view lists/filters packs+units by class/subject/grade/topic/status.
- [ ] Fork creates a new run seeded from a source run's contract/blueprint, linked via `forked_from_run_id`; the source is never mutated.
- [ ] Variant regeneration (e.g. different difficulty/methodology) works from an approved pack.
- [ ] export-my-data returns a portable bundle of the teacher's data; account erasure cascades across runs/artifacts/profiles/outcomes.

## Detailed test suite

(Real DB.)

- [ ] `services/gateway/tests/test_pack_library.py`: library filters return the correct packs/units per class/topic; cross-teacher isolation holds.
- [ ] `services/gateway/tests/test_fork_run.py`: forking creates a linked new run; the source is unchanged; lineage is queryable.
- [ ] `services/gateway/tests/test_data_portability.py`: export-my-data bundles all teacher data; account erasure cascades and leaves nothing behind.
- [ ] Run `uv run pytest services/gateway/tests/test_pack_library.py services/gateway/tests/test_fork_run.py services/gateway/tests/test_data_portability.py -v`.

## Blocked by

- .scratch/topic-decomposition/002-unit-persistence-and-migration.md
