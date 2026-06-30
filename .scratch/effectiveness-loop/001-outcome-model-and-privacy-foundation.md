---
title: Student-outcome data model, question KC tagging, and privacy foundation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The longitudinal foundation for measuring learning (ADR — effectiveness loop). A separate cross-run subsystem, not a pipeline stage (the pipeline reads mastery at planning time and writes a delivery record post-export).

- **Question KC tagging**: add `kc_ids: list[str]` to the question contract so each question maps to the `KnowledgeComponent`(s) it tests — without this, attempts can't be attributed to KCs.
- **Data model** (Pydantic, `common/contracts/`, `schema_version` per ADR-012): `StudentAttempt` (`student_pseudonym × question/kc × correct/score × timestamp × delivery_id`), `StudentKCState` (`student_pseudonym × kc × mastery × params`), `DeliveryRecord` (pack/KCs delivered to whom, written post-export). Outcome store tables (per teacher).
- **Privacy (PDPD 13/2023, minor data)**: store **pseudonym + KC-mastery + score only** (raw responses stay at Google/source); a **guardian-consent gate** is a precondition before capture is enabled for a class/student; retention/erasure **extends the `class_profiles`/`retention.py`/`purge.py` machinery** (topic-decomposition 013) — erasure cascades to attempts, KC-state, delivery records, snapshots.
- **Pipeline read hook**: a typed accessor `mastery_for(class, kcs)` the planner uses (consumed in issue 005). **Pipeline write hook**: a post-export `DeliveryRecord` write (non-blocking).

## Acceptance criteria

- [ ] Question contract carries `kc_ids`; existing questions default to empty (backward-compatible) with a path to backfill.
- [ ] `StudentAttempt`/`StudentKCState`/`DeliveryRecord` contracts + outcome-store tables exist, per-teacher, with `schema_version` and an Alembic migration applied by `make migrate`.
- [ ] Only pseudonym + KC-mastery + score are persisted; no raw student PII in the outcome store.
- [ ] A guardian-consent gate blocks capture until consent is recorded for the class/student.
- [ ] Retention/erasure covers the outcome store and cascades on teacher-initiated erasure.
- [ ] A non-blocking post-export `DeliveryRecord` write hook exists; a `mastery_for(...)` read accessor exists (consumers in later issues).

## Detailed test suite

(Real DB; deterministic.)

- [ ] `common/contracts/tests/test_outcome_contracts.py`: attempt/kc-state/delivery contracts parse, round-trip, carry `schema_version`; question `kc_ids` parses and is backward-compatible.
- [ ] `services/gateway/tests/test_outcome_store.py`: per-teacher CRUD on a real DB; cross-teacher access denied; only pseudonymized fields stored.
- [ ] `services/gateway/tests/test_consent_gate.py`: capture is blocked without consent; allowed after; erasure cascades to attempts/kc-state/delivery/snapshots.
- [ ] `services/gateway/tests/test_delivery_record_hook.py`: a completed export writes a `DeliveryRecord` without blocking the run.
- [ ] Run `make migrate` then `uv run pytest common/contracts/tests/test_outcome_contracts.py services/gateway/tests/test_outcome_store.py services/gateway/tests/test_consent_gate.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
