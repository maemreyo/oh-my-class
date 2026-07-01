---
title: Teacher preferences and reviewed lexical memory
status: done
labels: [ready-for-agent, memory, personalization]
created: 2026-07-01
---

## What to build

Extend the existing BaseStore memory direction from `priority-upgrades/002` for vocabulary-specific preferences and lexical knowledge. Store teacher corrections per teacher/tenant, and support optional reviewed promotion into shared lexical memory.

The memory model separates lexical truth from teaching style: shared records store source-grounded distinctions and edge cases; teacher/class records store tone, example style, anchor intensity, correction history, and class/run preferences.

## Acceptance criteria

- [x] Per-teacher vocabulary preference namespace stores tone, depth, example style, anchor intensity, and correction history.
- [x] Per-class/run context can influence audience level, CEFR/exam target, and topic context.
- [x] Term-distinction records are reusable across clusters with overlapping terms.
- [x] Cluster snapshots preserve exact generated/reviewed content for audit and re-render.
- [x] Shared lexical DB updates require explicit reviewed promotion and are not automatic.
- [x] Absent memory entries gracefully fall back to defaults.

## Detailed test suite

- [x] `packages/agents/tests/test_vocabulary_teacher_preferences.py`: teacher correction writes and later reads as a preference.
- [x] `packages/agents/tests/test_vocabulary_lexical_memory.py`: term-distinction record is reused in a variant cluster.
- [x] `packages/agents/tests/test_vocabulary_shared_lexical_review.py`: shared DB promotion requires reviewed state.
- [x] `packages/agents/tests/test_vocabulary_memory_defaults.py`: absent BaseStore entries do not crash or inject empty prompt junk.
- [x] Regression: `priority-upgrades/002` teacher/class memory behavior remains unchanged.

## Completion notes

- Added vocabulary-specific BaseStore namespaces in `packages/agents/teaching_pack/store_namespaces.py`.
- Added `packages/agents/teaching_pack/vocabulary_memory.py` for teacher preferences, per-class/run context, teacher/shared lexical distinctions, reviewed shared promotion, and exact cluster snapshots.
- Shared lexical promotion requires `reviewed=True`; teacher-scoped records remain private and reusable for overlapping term clusters.
- Verified with focused memory suites plus existing teacher-memory regression and a manual InMemoryStore smoke check.

## Blocked by

- `002-cluster-workflow-persistence.md`
- `004-lexical-grounding-profile.md`
- `009-projections-and-structured-editor.md`
- `priority-upgrades/002` (done ✅) — BaseStore teacher/class memory substrate
