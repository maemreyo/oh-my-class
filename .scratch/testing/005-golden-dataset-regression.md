---
title: Golden dataset and nightly regression
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

A curated golden dataset + nightly regression for the full system, generalizing the topic-decomposition eval harness (topic-decomposition 018) to the whole pack pipeline.

- **Golden set**: 50+ representative inputs (single-lesson packs + multi-session units) spanning subjects, grades, locales (VN + EN), and methodologies.
- **Scoring**: invariant + semantic-similarity scoring (not exact-match) + DeepEval G-Eval 3-vote majority (issue 004). Track a baseline cohort; flag regressions vs baseline.
- **Cadence**: nightly / pre-release (`real_llm` tier), with a token-budget ceiling for the run (fail loud if exceeded).
- **Drift detection**: alert when scores drop below baseline thresholds (model/prompt drift).

## Acceptance criteria

- [ ] A versioned golden dataset (≥50 items) spans subjects/grades/locales/methodologies, single-lesson and unit.
- [ ] Nightly regression scores each item via invariants + semantic similarity + G-Eval majority, compared to a baseline cohort.
- [ ] A token-budget ceiling bounds the nightly run; exceeding it fails loud.
- [ ] Score regressions vs baseline are flagged with the offending items.
- [ ] Results are logged to Langfuse for trend tracking.

## Detailed test suite

(Real LLM via 9router `:20228` / `4omc`; nightly.)

- [ ] `tests/eval/test_golden_dataset.py`: every golden item meets its invariant + threshold; a seeded regression (degraded prompt) drops below baseline and is flagged.
- [ ] `tests/eval/test_golden_budget.py`: a stubbed over-budget run fails loud.
- [ ] Coverage check: the dataset spans the required subject/grade/locale/methodology matrix.
- [ ] Run `uv run pytest -m real_llm tests/eval/test_golden_dataset.py -v` (nightly).

## Blocked by

- .scratch/testing/004-deepeval-quality-metrics.md
