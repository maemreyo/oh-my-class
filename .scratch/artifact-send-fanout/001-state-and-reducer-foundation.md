---
title: State and reducer foundation for artifact generation cycles
status: done
labels: [done]
created: 2026-07-01
---

## What to build

Add the state foundation required for LangGraph `Send` artifact fan-out without changing runtime behavior yet.

The teaching-pack graph needs a durable generation-cycle concept so reducer-backed branch output cannot leak across retries, scoped regeneration, or checkpoint replay. `artifact_chunks` already exists as a reducer-backed staging channel; this slice completes the missing sibling status channel and generation metadata.

Build:

- `artifact_generation_id` / revision field on `TeachingPackState` for the current generation cycle.
- `artifact_workflow_states` on `TeachingPackState` with a deterministic id-keyed reducer, analogous to `stable_merge_artifacts`.
- Reducer tests proving workflow states merge deterministically across all arrival orders and overwrite by stable id.
- Pure helpers for filtering current-generation chunks/states so fan-in can ignore stale reducer values.
- Documentation comments that make the state roles explicit: `artifact_chunks` = branch staging; `artifact_workflow_states` = branch status; `artifacts` = canonical downstream output.

Do not wire `Send` or change `_artifact_workflow` behavior in this slice.

## Acceptance criteria

- [x] `TeachingPackState` has a reducer-backed `artifact_workflow_states` channel and generation-cycle metadata.
- [x] The workflow-state reducer is deterministic under permutation, idempotent on replay, and overwrites by `workflow_id` or `artifact_id`.
- [x] Helpers can filter chunks and workflow states to only the current `artifact_generation_id`.
- [x] Existing sequential artifact generation tests continue to pass unchanged.
- [x] Architecture comments in the touched state/reducer code clearly distinguish staging channels from canonical `artifacts`.

## Detailed test suite

- [x] `packages/agents/tests/test_reducer_order_stable.py`: add workflow-state permutation/idempotency tests.
- [x] `packages/agents/tests/teaching_pack/test_artifact_generation_state.py`: generation id filtering excludes stale chunks/states and preserves current-cycle data.
- [x] Regression: run existing `packages/agents/tests/teaching_pack/test_artifact_workflow_node.py` and `packages/agents/tests/test_reducer_order_stable.py`.
- [x] LSP diagnostics clean on changed Python files.

## Verification

- 2026-07-01: `uv run pytest packages/agents/tests/test_reducer_order_stable.py packages/agents/tests/teaching_pack/test_artifact_generation_state.py packages/agents/tests/teaching_pack/test_artifact_workflow_node.py -q` → `27 passed`.
- 2026-07-01: LSP diagnostics clean for `packages/agents/teaching_pack/reducers.py`, `packages/agents/teaching_pack/nodes.py`, `packages/agents/tests/test_reducer_order_stable.py`, and `packages/agents/tests/teaching_pack/test_artifact_generation_state.py`.

## Blocked by

None - can start immediately.
