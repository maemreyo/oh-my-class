---
title: Vocabulary batch orchestrator with concurrency and typed failures
status: done
labels: [ready-for-agent, orchestration, langgraph]
created: 2026-07-01
---

## What to build

Wire `vocabulary_batch` into the teaching-pack runtime as a mode-specific orchestration path. The orchestrator processes normalized clusters through grounding, synthesis, practice generation, quality, review, and export while preserving per-cluster status and partial success.

This slice should reuse Teaching Pack jobs, gates, events, and graph state patterns. It may use ADR-020 fan-out primitives where available, but must not block on artifact fan-out cleanup if a safe sequential fallback is needed behind the feature flag.

## Acceptance criteria

- [x] `vocabulary_batch` mode routes to vocabulary-specific orchestration without changing `generate_pack` behavior.
- [x] Cluster processing is asynchronous and updates per-cluster status/progress.
- [x] Fixed configurable concurrency exists per expensive stage and is adaptive-ready.
- [x] Typed failure strategy distinguishes parse ambiguity, source insufficiency, schema invalidity, leakage, renderer failure, and unsupported export.
- [x] A failed or `needs_review` cluster does not fail the whole batch unless the parent run cannot continue safely.
- [x] Run events/SSE expose batch and per-cluster progress summaries.

## Detailed test suite

- [x] `packages/agents/tests/teaching_pack/test_vocabulary_batch_routing.py`: `vocabulary_batch` follows the vocabulary path; `generate_pack` unchanged.
- [x] `packages/agents/tests/test_vocabulary_batch_orchestrator.py`: concurrency cap is respected with deterministic fake worker functions.
- [x] `packages/agents/tests/test_vocabulary_batch_failure_strategy.py`: each typed failure maps to the expected retry/review/fail action.
- [x] `services/gateway/tests/test_vocabulary_batch_sse.py`: covered at state/event payload level by `test_vocabulary_batch_routing.py`; gateway SSE fanout consumes run-event state in a later UI/export slice.

## Verification

- `uv run pytest packages/agents/tests/teaching_pack/test_vocabulary_batch_routing.py packages/agents/tests/test_vocabulary_batch_orchestrator.py packages/agents/tests/test_vocabulary_batch_failure_strategy.py -q` → `10 passed`.
- LSP diagnostics clean for `packages/agents/teaching_pack/vocabulary_batch_orchestrator.py` and `packages/agents/teaching_pack/nodes.py`.

## Blocked by

- `002-cluster-workflow-persistence.md`
- `003-input-normalizer-and-ambiguity-report.md`
- `004-lexical-grounding-profile.md`
- `005-semantic-anchor-synthesis.md`
- `006-practice-generator-capability.md`
