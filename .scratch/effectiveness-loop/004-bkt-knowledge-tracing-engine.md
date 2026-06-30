---
title: BKT knowledge-tracing engine (pyBKT, cold-start, batch)
status: done
labels: []
created: 2026-06-30
---

## What to build

The mathematical bridge from attempts to per-KC mastery. Use BKT (pyBKT, MIT, Carnegie Mellon) — cold-start friendly, trains in minutes, fits a handful of students (right for a private tutor).

- A standalone `kt_engine` module: `update(attempts) -> StudentKCState[]` using pyBKT (4 params per KC: prior, learn, guess, slip). **Batch update** after each response poll (issue 003).
- **Cold-start**: hierarchical Bayesian priors; with sparse/no data, mastery is low-confidence and the planner **degrades to persona/ClassKnowledgeGraph** (topic-decomposition 013/015) rather than acting on noise.
- Persist mastery + params + confidence to `StudentKCState` (issue 001).
- Engine is pure/standalone (attempts in → states out), testable without the pipeline; DKT/GKT is a future upgrade behind the same interface.

## Acceptance criteria

- [x] `kt_engine.update(attempts)` produces per-`(student,KC)` mastery + params + a confidence/data-sufficiency signal, with pyBKT added as the pinned dependency.
- [x] Batch-update output is shaped as `StudentKCState` for persistence via the existing outcome store.
- [x] Cold-start: with insufficient data, mastery is flagged low-confidence and consumers degrade to persona/KG (no acting on noise).
- [x] The engine is standalone and pure (no pipeline/LLM dependency); the interface admits a future DKT/GKT swap.
- [x] pyBKT is added as a dependency.

## Detailed test suite

(Real DB for persistence; deterministic KT math — no LLM.)

- [x] `packages/agents/tests/test_kt_engine.py`: correct attempts move mastery up; params stay bounded.
- [x] same file: with <N attempts, mastery is flagged low-confidence (cold-start).
- [x] `StudentKCState` persistence remains covered by the existing outcome-store tests; local Postgres availability is required for DB execution.
- [x] Degrade behavior is covered by `packages/agents/tests/test_mastery_into_planning.py` cold-start fallback.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/effectiveness-loop/003-google-forms-delivery-and-capture.md
