---
title: DeepEval quality metrics mapped to quality layers (9router-backed)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add DeepEval as the pytest metric layer for content/quality, routed through 9router and mapped onto the real quality gates (depends on runtime-parity 001 wiring the 6-layer into the authoritative path).

- **Layer 2 (content)**: `HallucinationMetric` + `FaithfulnessMetric` over generated artifacts; RAGAS-style faithfulness for the Researcher's sourced claims.
- **Layer 4 (LLM-as-Judge)**: DeepEval custom G-Eval metric mirroring the existing 3-vote majority rubric, judge routed via 9router (`4omc`).
- **Layer 6 (export readiness)**: DeepEval dataset eval + majority vote.
- All metrics: 9router-backed judge, offline mode (no telemetry), results logged to Langfuse. `real_llm` tier (nightly), not per-commit.

These metrics validate the **real** quality path; they are not a substitute for the in-pipeline gates (runtime-parity 001) but a test-time assertion over them.

## Acceptance criteria

- [ ] Hallucination + faithfulness metrics run over generated artifacts and flag injected factual errors.
- [ ] A DeepEval G-Eval metric reproduces the 3-vote-majority rubric semantics, judge via 9router.
- [ ] Export-readiness dataset eval + majority vote runs over a sample.
- [ ] All DeepEval judges use 9router (`4omc`), offline; results land in Langfuse.
- [ ] Metrics are `real_llm`-marked (nightly), with invariant/threshold assertions (not exact-match).

## Detailed test suite

(Real LLM via 9router `:20228` / `4omc`.)

- [ ] `tests/quality/test_hallucination_faithfulness.py`: an artifact with an injected factual error fails `HallucinationMetric`; a faithful one passes.
- [ ] `tests/quality/test_geval_majority.py`: the DeepEval G-Eval metric scores a known-good vs known-bad pack consistently with the existing rubric.
- [ ] `tests/quality/test_export_readiness_dataset.py`: a sample dataset passes the majority-vote export gate; a seeded-bad item fails.
- [ ] Routing test: every DeepEval metric call hits 9router, not OpenAI; a result appears in Langfuse.
- [ ] Run `uv run pytest -m real_llm tests/quality -v`.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
- .scratch/runtime-parity/001-six-layer-quality-gate-adapter.md
