---
title: Wave-based Send router and fan-in materializer
status: done
labels: [ready-for-agent]
created: 2026-07-01
---

## What to build

Wire the first graph-level path for LangGraph-native artifact fan-out. It was initially introduced behind a rollout flag and is now the default path after issue `008`.

`artifact_workflow` becomes a coordinator for generation cycles. It computes dependency waves, issues `Send("generate_one_artifact", payload)` for the current wave, then a fan-in materializer converts current-generation chunks into canonical `artifacts`. The graph loops wave-by-wave until all required waves are complete or a required dependency fails.

The canonical wave plan is:

- Wave 0: `lesson`
- Wave 1: `worksheet`, `quiz`, `drill`
- Wave 2: `recap`

Use reusable planning helpers extracted from the existing `ArtifactOrchestrator` design, respecting package boundaries (`packages/*` must not import from `services/*`).

## Acceptance criteria

- [x] `build_teaching_pack_graph` registers `generate_one_artifact` as a real node name and wires a conditional edge that returns `list[Send]`.
- [x] The router issues only the current dependency wave and never fans out all artifact types at once.
- [x] The fan-in materializer reads current-generation `artifact_chunks` and `artifact_workflow_states`, writes canonical `artifacts`, and advances or blocks the wave state.
- [x] If a required dependency fails, dependent artifacts are marked skipped and the next wave is not issued.
- [x] Before issue `008`, the rollout flag off path kept the existing imperative `_artifact_workflow` behavior unchanged; after issue `008`, the old path is explicit rollback-only.

## Detailed test suite

- [x] `packages/agents/tests/teaching_pack/test_artifact_send_graph.py`: fake worker proves lesson runs before worksheet/quiz/drill and recap waits for lesson+quiz.
- [x] Same file: one wave branch failure prevents dependent wave while preserving passed sibling artifacts.
- [x] Same file: reducer completion order does not change final `artifacts` ordering.
- [x] Same file: rollback path calls existing `content_creator_node` behavior.
- [x] Run a focused graph invocation with in-memory checkpointer and fake worker; no real LLM required for topology tests.
- [x] LSP diagnostics clean on changed Python files.

## Completion evidence

- Implemented the initial rollout flag; issue `008` later made Send default and replaced rollout gating with explicit rollback via `OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1`.
- Added `packages/agents/teaching_pack/artifact_fanout.py` for wave coordination, current-generation fan-in, dependency blocking, and `Send("generate_one_artifact", payload)` routing.
- Registered `generate_one_artifact` in `build_teaching_pack_graph`; issue `008` keeps the old imperative `_artifact_workflow` behavior only as an explicit rollback path.
- Verified `uv run pytest packages/agents/tests/teaching_pack/test_artifact_send_graph.py packages/agents/tests/teaching_pack/test_generate_one_artifact.py packages/agents/tests/teaching_pack/test_artifact_generation_state.py packages/agents/tests/teaching_pack/test_artifact_workflow_node.py packages/agents/tests/test_reducer_order_stable.py -q` → `38 passed`.
- Verified LSP diagnostics clean for changed Python files.

## Blocked by

- `.scratch/artifact-send-fanout/001-state-and-reducer-foundation.md`
- `.scratch/artifact-send-fanout/002-generate-one-artifact-node.md`
