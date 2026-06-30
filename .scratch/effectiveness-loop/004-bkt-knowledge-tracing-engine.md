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

- [ ] `kt_engine.update(attempts)` produces per-`(student,KC)` mastery + params + a confidence/data-sufficiency signal, via pyBKT.
- [ ] Batch update runs after a response poll; mastery is persisted to `StudentKCState`.
- [ ] Cold-start: with insufficient data, mastery is flagged low-confidence and consumers degrade to persona/KG (no acting on noise).
- [ ] The engine is standalone and pure (no pipeline/LLM dependency); the interface admits a future DKT/GKT swap.
- [ ] pyBKT is added as a dependency.

## Detailed test suite

(Real DB for persistence; deterministic KT math — no LLM.)

- [ ] `packages/agents/tests/test_kt_engine.py`: a sequence of correct/incorrect attempts moves mastery monotonically in the expected direction; params stay in [0,1].
- [ ] same file: with <N attempts, mastery is flagged low-confidence (cold-start).
- [ ] `services/gateway/tests/test_kt_batch_update.py`: a response poll triggers a batch update persisting `StudentKCState` on a real DB.
- [ ] Degrade test: low-confidence mastery causes the `mastery_for` accessor to signal "defer to persona/KG".
- [ ] Run `uv run pytest packages/agents/tests/test_kt_engine.py services/gateway/tests/test_kt_batch_update.py -v`.

## Blocked by

- .scratch/effectiveness-loop/003-google-forms-delivery-and-capture.md
