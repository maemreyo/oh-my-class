---
title: BKT knowledge-tracing engine (pyBKT, cold-start, batch)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The mathematical bridge from attempts to per-KC mastery. Use BKT (pyBKT, MIT, Carnegie Mellon) — cold-start friendly, trains in minutes, fits a handful of students (right for a private tutor).

- A standalone `kt_engine` module: `update(attempts) -> StudentKCState[]` using pyBKT (4 params per KC: prior, learn, guess, slip). **Batch update** after each response poll (issue 003).
- **Cold-start**: hierarchical Bayesian priors; with sparse/no data, mastery is low-confidence and the planner **degrades to persona/ClassKnowledgeGraph** (topic-decomposition 013/015) rather than acting on noise.
- Persist mastery + params + confidence to `StudentKCState` (issue 001).
- Engine is pure/standalone (attempts in → states out), testable without the pipeline; DKT/GKT is a future upgrade behind the same interface.

## Acceptance criteria

- [ ] `kt_engine.update(attempts)` produces per-`(student,KC)` mastery + params + a confidence/data-sufficiency signal using a real pyBKT model, not a local fallback stamped as pyBKT.
- [x] Batch-update output is shaped as `StudentKCState` for persistence via the existing outcome store.
- [x] Cold-start: with insufficient data, mastery is flagged low-confidence and consumers degrade to persona/KG (no acting on noise).
- [x] The engine is standalone and pure (no pipeline/LLM dependency); the interface admits a future DKT/GKT swap.
- [ ] pyBKT is added as a dependency only when the runtime actually uses it.

## Audit correction — 2026-07-02

The previous implementation was false-green: it imported pyBKT only to survive an audit, monkeypatched sklearn metrics, discarded the model, ran the local Bayesian EMA, and stamped `pybkt_used=1.0`. That fake path has been removed. Current runtime honestly reports `local_bayesian_ema_used=1.0`; the real pyBKT engine remains to be implemented.

## Detailed test suite

(Real DB for persistence; deterministic KT math — no LLM.)

- [x] `packages/agents/tests/test_kt_engine.py`: correct attempts move local Bayesian EMA mastery up; params stay bounded.
- [x] same file: with <N attempts, mastery is flagged low-confidence (cold-start).
- [x] same file: incorrect attempts reduce mastery and unverified concept alignment flags low-trust mastery.
- [x] `StudentKCState` persistence remains covered by the existing outcome-store tests; local Postgres availability is required for DB execution.
- [x] Degrade behavior is covered by `packages/agents/tests/test_mastery_into_planning.py` cold-start fallback.
- [x] Run `uv run pytest packages/agents/tests/test_kt_engine.py -q`: `4 passed` for the honest local fallback.

## Verification

- `uv run pytest packages/agents/tests/test_kt_engine.py -q` → 4 passed for the local fallback; pyBKT acceptance remains open.

## Blocked by

- .scratch/effectiveness-loop/003-google-forms-delivery-and-capture.md
