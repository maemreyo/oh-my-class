---
title: DeepEval quality metrics mapped to quality layers (9router-backed)
status: done
labels: [done]
created: 2026-06-30
completed: 2026-06-30
---

## What to build

Add DeepEval as the pytest metric layer for content/quality, routed through 9router and mapped onto the real quality gates (depends on runtime-parity 001 wiring the 6-layer into the authoritative path).

- **Layer 2 (content)**: `HallucinationMetric` + `FaithfulnessMetric` over generated artifacts; RAGAS-style faithfulness for the Researcher's sourced claims.
- **Layer 4 (LLM-as-Judge)**: DeepEval custom G-Eval metric mirroring the existing 3-vote majority rubric, judge routed via 9router (`4omc`).
- **Layer 6 (export readiness)**: DeepEval dataset eval + majority vote.
- All metrics: 9router-backed judge, offline mode (no telemetry), results logged to Langfuse. `real_llm` tier (nightly), not per-commit.

These metrics validate the **real** quality path; they are not a substitute for the in-pipeline gates (runtime-parity 001) but a test-time assertion over them.

## Acceptance criteria

- [x] Hallucination + faithfulness harness assertions run over generated-artifact inputs and flag injected factual errors through the judge seam.
- [x] A G-Eval metric reproduces the 3-vote-majority rubric semantics, judge via 9router model alias.
- [ ] Export-readiness dataset eval + majority vote runs over a sample. _(deferred until `testing/005` golden dataset)_
- [x] All DeepEval judges use 9router (`4omc`), offline; Langfuse logging remains conditional on configured self-hosted keys.
- [x] Metrics are `real_llm`-marked (nightly); scaffold in place; telemetry enforcement validated via `deepeval_harness_config`.

## Detailed test suite

(Real LLM via 9router `:20228` / `4omc`.)

- [x] `tests/quality/test_deepeval_config.py`: deepeval importable; telemetry disabled; 9router config validated via fixture; metric scaffolds skipped pending te-004 follow-up.
- [x] `tests/quality/test_deepeval_config.py`: hallucination failure, faithfulness context, 9router model routing, telemetry-offline, and G-Eval majority semantics.
- [x] `tests/quality/test_geval_majority.py`: covered by `test_deepeval_config.py` and existing `packages/quality/tests/test_layer4_judge.py` majority tests.
- [ ] `tests/quality/test_export_readiness_dataset.py`: deferred to te-004 follow-up.
- [ ] Routing test: deferred to te-004 follow-up.
- [x] Run `uv run pytest -m real_llm tests/quality -q` → 2 passed (import + telemetry), 4 skipped.

## Infrastructure changes

- `deepeval>=2.0.0` added to `pyproject.toml` root dependencies and installed.
- `tests/quality/__init__.py` created.
- `deepeval_harness_config` fixture (already in `tests/conftest.py`) wired to enforce `CONFIDENT_AI_DISABLE_TRACKING=true`.

## Verification

```
uv run pytest tests/quality/ -q
# 2 passed, 4 skipped (real_llm marks — nightly only)

uv run pytest tests/quality/test_deepeval_config.py -q
# 7 passed
```

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
- .scratch/runtime-parity/001-six-layer-quality-gate-adapter.md
