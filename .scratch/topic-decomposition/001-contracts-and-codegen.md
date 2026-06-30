---
title: Topic-decomposition contracts and Zod codegen
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the typed contract foundation for topic decomposition so a multi-session topic can be represented as structured data, and so backend and frontend share one source of truth via the existing Pydantic → JSON Schema → Zod codegen.

Split **domain** contracts from **transport/view** contracts so SoC is preserved:

- `common/contracts/lesson_sequence.py` (domain): `KnowledgeComponent`, `SessionPlan`, `PrerequisiteEdge`, `LessonSequence`.
- `common/contracts/unit_view.py` (transport): `UnitView` aggregate read model + unit SSE event payloads.
- `common/contracts/run_contract.py` (extend): `PipelineMode` gains `"plan_unit"`; add `DecompositionIntent { target_sessions, session_length_minutes, source }`.

This slice introduces contracts, validators, fixtures, and codegen only. It must not wire the pipeline, persistence, or UI; later slices consume these types.

Decision-rich shape (from ADR-017):

```python
SessionPlan:
    session_id: str            # stable domain key, e.g. "S01" — never changes on reorder
    order_index: int           # display ordering only
    child_run_id: str | None   # set after fan-out
    title; sub_topic; duration_minutes (10..90)
    learning_objectives (1..5); bloom_level_primary
    knowledge_components: list[KnowledgeComponent]   # NEW KCs only, max_length = 4 (CLT)
    recalled_kc_ids: list[str]                       # references, not counted toward load
    prerequisite_sessions: list[str]                 # session_id refs (authoritative for orchestration)
    methodology_primary: MethodologyTag; methodology_secondary: MethodologyTag | None

LessonSequence:
    topic; grade_level; subject; locale
    total_sessions (1..20); total_duration_minutes
    sessions: list[SessionPlan]
    prerequisite_edges: list[PrerequisiteEdge]   # KC-level, advisory/optional
    grounding_status: "grounded" | "partial" | "ungrounded"
    confidence: float; open_questions: list[str]; rationale
```

## Acceptance criteria

- [ ] Pydantic v2 contracts for `LessonSequence`, `SessionPlan`, `KnowledgeComponent`, `PrerequisiteEdge` exist in `common/contracts/lesson_sequence.py` with Field bounds matching ADR-017 (KC `max_length=4`, duration 10–90, `total_sessions` 1–20).
- [ ] `SessionPlan` uses a stable string `session_id` as the prerequisite key; `order_index` is separate; `prerequisite_sessions` references `session_id` values, not indices.
- [ ] `MethodologyMetadata` is reused at session level via `methodology_primary` (+ optional secondary) consistent with `common/contracts/lesson_plan.py`.
- [ ] `unit_view.py` defines `UnitView` (parent meta + sequence + per-session status/progress + unit aggregate + coherence warnings + `cursor`) and the unit event payload models, with a monotonic `cursor` field.
- [ ] `RunContract.mode` accepts `"plan_unit"`; `DecompositionIntent` is added and is optional/backward-compatible.
- [ ] Generated Zod/TS output includes all new domain + transport types, registered in `scripts/generate_zod_schemas.py` `MODELS`.
- [ ] Fixtures cover at least one Vietnamese math chủ đề, one English grammar topic, and one science topic, each as a valid multi-session `LessonSequence`.

## Detailed test suite

- [ ] `common/contracts/tests/test_lesson_sequence_contracts.py`: valid VN-math/English/science fixtures parse as `LessonSequence` and round-trip via `model_dump()`.
- [ ] `common/contracts/tests/test_lesson_sequence_contracts.py`: a `SessionPlan` with 5 `knowledge_components` raises `ValidationError` (CLT ≤4); duration outside 10–90 raises; empty `learning_objectives` raises.
- [ ] `common/contracts/tests/test_lesson_sequence_contracts.py`: `prerequisite_sessions` referencing an unknown `session_id` is detectable (model-level or validator hook), and reordering `order_index` does not change `session_id` references.
- [ ] `common/contracts/tests/test_run_contract_plan_unit.py`: `mode="plan_unit"` and `DecompositionIntent` parse; existing `generate_pack`/`diagnose_then_generate` contracts parse unchanged (no migration breakage).
- [ ] `common/schemas` parity test: generated Zod schemas for `lesson_sequence`, `unit_view`, and `decomposition_intent` match the Pydantic JSON schema field names and required/optional status.
- [ ] Run `make check-schemas` (or `generate:schemas` + `verify:schemas`) and `uv run pytest common/contracts/tests -v --cov=common/contracts --cov-fail-under=95`.

## Blocked by

None - can start immediately
