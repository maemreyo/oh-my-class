---
title: Unit observability and golden-topics decomposition eval harness
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make units observable in production and pin the **pedagogical** quality of decomposition (not just schema validity) with a property-based eval over real LLM output (ADR-017 §Test).

- **Observability**: emit unit-scoped run events/metrics — `unit.created`, fan-out size, per-session status transitions, `grounding_status`, confidence, validator issues, coherence warnings, teacher edits at the unit gate, blocked/override counts, partial-vs-complete, per-unit token/cost rollup. Surface them through the existing event/observability substrate (Langfuse tags + run events).
- **Eval harness**: `tests/eval/test_decomposition_quality.py` runs a set of golden topics (e.g. "Phân số — Toán Lớp 5", "Present Tenses", "Quang hợp — KHTN 6") through `unit_planner` with the **real LLM (9router port 20228, model `4omc`)** and asserts invariants — not exact sequences — so it is robust to nondeterminism.

The eval runs nightly / pre-release, not per-commit.

## Acceptance criteria

- [ ] Unit-scoped events/metrics listed above are emitted and tagged consistently with existing observability.
- [ ] Per-unit token/cost is aggregated from children.
- [ ] The eval harness exists with ≥3 golden topics spanning subjects and locales.
- [ ] Eval invariants: acyclic DAG, ≥2 Bloom levels, ≤4 KC/session, duration drift ≤10%, session count within the grounded norm, every session has a methodology, all prerequisite references resolve, `grounding_status` is `grounded`/`partial` for known topics.
- [ ] The eval is wired to a nightly/pre-release target, separate from per-commit CI.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`.)

- [ ] `tests/eval/test_decomposition_quality.py`: each golden topic yields a sequence satisfying all invariants above; failures report which invariant broke for which topic.
- [ ] Observability test: a completed unit's events include `grounding_status`, confidence, fan-out size, edit counts, and a token/cost rollup.
- [ ] Drift sentinel: a deliberately weak prompt/model variation that violates an invariant is caught by the eval (the harness fails, proving it is not a no-op).
- [ ] Cost-rollup test: the parent's aggregated token/cost equals the sum across its children.
- [ ] Run `uv run pytest tests/eval/test_decomposition_quality.py -v` (nightly/pre-release) and the observability unit tests in CI.

## Blocked by

- .scratch/topic-decomposition/006-unit-planner-agent.md
- .scratch/topic-decomposition/010-unit-orchestrator.md
