---
title: Per-teacher/class memory via BaseStore
status: done
labels: [memory, personalization, teacher-facing]
created: 2026-07-01
---

## What to build

The `BaseStore` substrate is already wired (`agent-interaction/002a` done: `open_teaching_pack_store`, 6 namespace factories, `build_teaching_pack_graph(store=)` injected). It is **not yet read or written by any stage node**. The system has no memory of a teacher's preferences, vocabulary context, or frequently-edited artifact types across runs.

Build a minimal per-teacher + per-class memory layer on top of the existing store:

**What to persist (scope: reads + writes inside stage nodes):**
1. **Approval history** — per-gate (`content_approval`): how often the teacher rejects/edits vs. approves, and which artifact types are most-edited. Written at `teacher_approval` gate close.
2. **Difficulty skew** — teacher's revealed preference: if they consistently edit the generated difficulty down/up (inferred from `ContractRevision` edits on `lesson_plan.difficulty_level`). Written at contract-confirmation close.
3. **Vocabulary context** — per-class profile: key terms/concepts the teacher has introduced in prior runs for the same class (class_id). Written at `export_finalize` complete. Read by `planner_node` to avoid re-teaching introduced terms, or to build on them.
4. **Artifact-type preference** — which artifact types the teacher keeps vs. deletes across runs. Written at `export_finalize`.

**Namespaces** (use the already-defined namespace factories in `store_namespaces.py`):
- `teacher_preferences/{teacher_id}` — approval_history, difficulty_skew, artifact_type_preference
- `class_context/{class_id}` — vocabulary, prior_lesson_topics

**Wire into planner prompt:** `_planning_blueprint` reads `class_context/{class_id}` and injects a "prior vocabulary: [...]" and "topics covered: [...]" hint into the planner prompt (if store entry exists and is non-empty).

This is NOT semantic search / embeddings — pure key-value retrieval by teacher_id / class_id. Semantic index is `agent-interaction/002b` (still parked; do not conflate).

## Acceptance criteria

- [ ] Stage nodes write to BaseStore at appropriate gates (approval history at gate close, vocabulary at export complete, difficulty at contract revision).
- [ ] `_planning_blueprint` reads `class_context/{class_id}` and includes vocabulary/topic context in the planner prompt when present.
- [ ] Store entries have TTL set per the namespace conventions in `store_namespaces.py`.
- [ ] A teacher with `N` prior runs for the same class sees their vocabulary context appear in the planner prompt for run `N+1`.
- [ ] Absent store entries → no crash, no prompt injection, graceful skip.

## Detailed test suite

(Deterministic-logic tests without LLM for store read/write; real LLM needed for planner-prompt injection test.)

- [ ] `packages/agents/tests/test_teacher_memory_store.py` (no LLM): mock a BaseStore; run `teacher_approval` gate close → verify expected keys written to `teacher_preferences/{teacher_id}`. Verify that absent entries don't cause errors in node read path.
- [ ] `packages/agents/tests/test_planner_class_context_injection.py` (real LLM via 9router): seed `class_context/test_class_01` with `{vocabulary: ["hình chữ nhật", "diện tích"], topics: ["geometry basics"]}` → run `_planning_blueprint` → verify planner output references or acknowledges the seeded vocabulary.
- [ ] TTL: verify entries older than the configured TTL window are expired from the store (mock store).

## Blocked by

- agent-interaction/002a (done ✅) — BaseStore substrate already wired
