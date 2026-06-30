---
title: Test tiering — fast deterministic vs real-LLM eval
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Keep CI fast and green while preserving the project policy of real DB + real LLM tests. Real-LLM tests (9router) are slow/costly/variable; real-DB tests are cheap. Tier on the LLM dependency.

- A `@pytest.mark.real_llm` marker. **Per-commit CI** runs deterministic + **real-DB** tests and **excludes** `real_llm`. **Nightly / pre-release** runs the `real_llm` eval suite.
- Real-LLM tests assert **invariants** (not exact output), with bounded retry / quarantine for flakiness, over a bounded golden set (consistent with topic-decomposition issue 018 — promote that pattern repo-wide).
- A **token-budget ceiling** for the nightly eval run; fail loud if exceeded.

## Acceptance criteria

- [ ] A `real_llm` marker exists; per-commit CI excludes it and still exercises real-DB paths; nightly/pre-release includes it.
- [ ] Real-LLM tests assert invariants and tolerate nondeterminism (retry/quarantine), not exact-string matches.
- [ ] The nightly eval enforces a token-budget ceiling and fails loud when exceeded.
- [ ] Documentation states the tiering policy and how to run each tier (`make test` vs a nightly target).

## Detailed test suite

- [ ] `tests/test_tiering_markers.py`: collecting per-commit CI yields zero `real_llm` tests; the nightly selector yields the eval suite.
- [ ] A representative `real_llm` test demonstrates invariant assertions + bounded retry.
- [ ] Budget-ceiling test: a stubbed over-budget eval run fails loud.
- [ ] Run `uv run pytest -m "not real_llm" -q` (fast tier) and `uv run pytest -m real_llm -q` (eval tier) succeed independently.

## Blocked by

None - can start immediately
