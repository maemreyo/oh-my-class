---
title: ClassProfile entity and persona-driven planning
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make student persona durable and remembered across units, and let it drive teaching-effectiveness decisions (ADR-017 §Persona memory). Today `class_info` is an untyped per-run dict and nothing persists a class.

- `common/contracts/class_profile.py`: `ClassProfile` (grade/age_band, subject_focus, language, class_size, proficiency_level, `known_misconceptions[]`, `prior_knowledge_gaps[]`, learning_preferences, attention_span_band, differentiation_needs, `prior_topics_taught[]`, optional `students: list[StudentProfile]` for small/1-on-1). Reuse the existing `StudentProfile` contract.
- Persistence: a `class_profiles` table owned by the teacher; reusable across runs/units.
- Snapshot: at unit creation the active `ClassProfile` is **snapshotted** (copied, not referenced) into the parent's `persona_snapshot` so the unit stays coherent with the persona at plan time.
- Planning input: persona is a first-class input to `unit_planner` (and inherited by child planners via issue 009), influencing duration (age-band), methodology bias, assume-vs-reteach, and difficulty.
- Backward-compat: existing `class_info` dicts are accepted and mapped into a `ClassProfile`; single-lesson runs benefit too.

## Acceptance criteria

- [ ] `ClassProfile` Pydantic contract exists and is codegen'd to Zod (registered in `MODELS`).
- [ ] `class_profiles` table + store methods (create/read/update per teacher) exist with an Alembic migration applied by `make migrate`.
- [ ] Unit creation writes a `persona_snapshot` (deep copy) onto the parent; later edits to the source `ClassProfile` do not change an existing unit's snapshot.
- [ ] `unit_planner` consumes persona and demonstrably varies output (duration/methodology/assume-vs-reteach) by persona.
- [ ] Legacy `class_info` dicts map cleanly into `ClassProfile`; existing single-lesson runs are unaffected.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [ ] `common/contracts/tests/test_class_profile.py`: valid profiles (aggregate and with `students`) parse and round-trip; a legacy `class_info` dict maps into a `ClassProfile`.
- [ ] `services/gateway/tests/test_class_profile_store.py`: create/read/update a class profile per teacher on a real DB; cross-teacher access denied.
- [ ] `services/gateway/tests/test_persona_snapshot.py`: a unit's `persona_snapshot` is immutable to subsequent edits of the source profile.
- [ ] `packages/agents/tests/test_persona_driven_planning.py`: two personas (e.g. weak-prerequisites vs advanced) over the same topic yield different assume-vs-reteach / duration decisions from `unit_planner`.
- [ ] Run `make migrate` then `uv run pytest common/contracts/tests/test_class_profile.py services/gateway/tests/test_class_profile_store.py services/gateway/tests/test_persona_snapshot.py packages/agents/tests/test_persona_driven_planning.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
- .scratch/topic-decomposition/002-unit-persistence-and-migration.md
