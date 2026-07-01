---
title: Concurrency and budget wiring for artifact Send fan-out
status: done
labels: [ready-for-agent]
created: 2026-07-01
---

## What to build

Add production-grade concurrency controls for artifact `Send` fan-out.

The domain layer controls which artifacts may run together by dependency wave and configured artifact parallelism. The LangGraph runtime layer receives top-level `RunnableConfig.max_concurrency`. The budget ledger records and guards resources but does not enforce parallelism.

Current `teaching_pack_thread_config(run_id)` only returns `{"configurable": {"thread_id": run_id}}` and its type alias is too narrow. Widen it to represent the real RunnableConfig shape, then pass `max_concurrency` when artifact fan-out is enabled.

## Acceptance criteria

- [x] `teaching_pack_thread_config` can return top-level `max_concurrency` alongside `configurable.thread_id`.
- [x] Runtime graph invocations use a configured artifact fan-out cap when the Send path is enabled.
- [x] The wave router never issues more Sends in a wave than the configured domain cap.
- [x] Budget code remains explicit that `parallel_artifacts` is caller-site enforced; no misleading ledger-only guard is introduced.
- [x] Config names and defaults are documented, bounded, and tested.

## Detailed test suite

- [x] `packages/agents/tests/teaching_pack/test_thread_config.py`: config shape includes top-level `max_concurrency` and preserves `thread_id`.
- [x] `packages/agents/tests/teaching_pack/test_artifact_send_concurrency.py`: fake worker tracks active count and proves the cap is respected.
- [x] `services/gateway/tests/test_worker_concurrency.py` regression: worker concurrency remains independent from per-run artifact fan-out concurrency.
- [x] `services/gateway/tests/test_budget_hardstop.py` regression: token/search/fetch budgets still behave as before.
- [x] LSP diagnostics clean on changed Python files.

## Completion evidence

- Widened `LangGraphRunnableConfig` to include optional top-level `max_concurrency` and wired `teaching_pack_thread_config()` to set it for artifact Send fan-out. Issue `008` later made the Send path default.
- Reused bounded `TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM` (`TeachingPackConfig.default_artifact_parallelism`, default `2`, bounds `1..8`) for both LangGraph runtime concurrency and the domain Send wave cap.
- Added wave-router cap tests proving capped waves issue only N Sends and later issue remaining branches.
- Added database-free executor config regression proving start/resume graph invocations receive the per-run fan-out cap independently of worker batch concurrency.
- Verified `uv run pytest packages/agents/tests/teaching_pack/test_thread_config.py packages/agents/tests/teaching_pack/test_artifact_send_concurrency.py packages/agents/tests/teaching_pack/test_artifact_send_graph.py packages/agents/tests/teaching_pack/test_send_scoped_regeneration.py services/gateway/tests/test_teaching_pack_executor_config.py services/gateway/tests/test_budget_hardstop.py -q` → `24 passed`.
- Attempted `services/gateway/tests/test_worker_concurrency.py`; local run was blocked by unavailable Postgres on `localhost:5432`, so independence is covered by `test_teaching_pack_executor_config.py` in this environment.
- Verified LSP diagnostics clean on changed Python files.

## Blocked by

- `.scratch/artifact-send-fanout/003-wave-router-and-fanin.md`
