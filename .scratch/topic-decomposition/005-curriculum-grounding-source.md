---
title: Curriculum grounding knowledge source and retrieval
status: done
labels: []
created: 2026-06-30
---

## What to build

Provide a retrievable grounding source so `unit_planner` decomposes from real curriculum constraints instead of hallucinating them (ADR-017 §Smart layers; report §3, §5). Package the GDPT-2018 / PPCT mapping, topic-to-lesson norms, age-band attention/duration tables, and Bloom/assessment distributions as a structured, queryable knowledge source — not hardcoded constants scattered across prompts.

`packages/agents/grounding/`:

- A structured reference store (e.g. typed records loaded from `data/` files) keyed by `(subject, grade, locale)` plus age-band lookups.
- A `retrieve_grounding(topic, grade, subject, locale) -> GroundingContext` function returning the matched curriculum norms (tiết/bài ranges, session length, Bloom distribution) and a `grounding_status` (`grounded` / `partial` / `ungrounded`).

Phase 1 uses structured retrieval only. Semantic retrieval over PPCT prose, if ever needed, must use `pgvector` on the existing Postgres — no new vector store.

## Acceptance criteria

- [x] Reference data for VN GDPT-2018 norms (per report §3.2–§3.3) and age-band tables (§5.1) is stored as structured data files, not inline literals.
- [x] `retrieve_grounding(...)` returns matched norms and a `grounding_status` that is `ungrounded` when no curriculum match exists.
- [x] The function is pure and side-effect free (no LLM); it is reusable by `unit_planner` and the validator.
- [x] Adding a new subject/grade is a data change, not a code change.

## Detailed test suite

(Deterministic — no DB/LLM.)

- [x] `packages/agents/tests/test_grounding_retrieval.py`: `(Toán, Lớp 5, vi-VN)` returns the documented chủ đề/tiết ranges and `grounded`.
- [x] same file: an unknown subject/grade returns `ungrounded` with no fabricated norms.
- [x] same file: age-band lookup returns the correct attention/duration band per grade (§5.1).
- [x] same file: session-length defaults resolve to 45 min for THCS/THPT and 35–45 for primary per `Thông tư 32/2020`.
- [x] Run `uv run pytest packages/agents/tests/test_grounding_retrieval.py -v`.

## Verification

- `uv run pytest packages/agents/tests/test_grounding_retrieval.py -q` → 4 passed.
- LSP diagnostics clean for `packages/agents/grounding/retrieval.py`, `packages/agents/grounding/models.py`.

## Blocked by

None - can start immediately
