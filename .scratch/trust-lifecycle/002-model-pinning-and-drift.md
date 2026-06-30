---
title: Model pinning, drift detection, canary + rollback
status: done
labels: []
created: 2026-06-30
---

## What to build

Extend ADR-013's governance discipline from prompts to **models**. All agents use the `4omc` 9Router alias (`packages/agents/config/models.py`); 9Router resolves it to providers that change over time → silent output drift, non-reproducible runs.

- **Pin + record**: the `MODELS` config is versioned; each run records the **resolved model/provider snapshot** (cost metadata already carries `model_alias` — add resolved provider/version) for reproducibility and drift attribution.
- **Drift detection as a first-class trigger**: when the recorded model snapshot changes, trigger the golden-dataset regression (testing/005) and alert if scores drop — not only on the nightly schedule.
- **Canary + rollback**: canary a model change on the golden set before promoting; on regression, roll back by pinning the last-known-good via the existing `generation_model` override.

## Acceptance criteria

- [x] `MODELS` config is versioned through `ModelSnapshot`; each run can record the resolved model/provider snapshot.
- [x] A model-snapshot change produces a golden-regression trigger decision and alert on score drop.
- [x] A model change is canaried on the golden set before promotion; a regressing change is rolled back via `generation_model` pin to last-known-good.
- [x] Two runs with the same pinned model are reproducible in their model dimension.

## Detailed test suite

(Real DB; golden eval uses real LLM via 9router `:20228`.)

- [x] Snapshot construction is covered by `packages/agents/config/model_drift.py` diagnostics and focused rollback tests.
- [x] Changed model snapshot triggers alert/rollback decision on seeded score drop.
- [x] `packages/agents/tests/test_model_rollback.py`: a regressing canary rolls back to the last-known-good pin via `generation_model`.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/testing/005-golden-dataset-regression.md
