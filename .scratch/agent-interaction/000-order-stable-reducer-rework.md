---
title: Order-stable index-keyed reducer for parallel state merge
status: done
labels: [done]
created: 2026-06-30
---

## What to build

A **deterministic, order-stable reducer** for any `TeachingPackState` channel that will receive concurrent `Send` writes — the hard prerequisite for parallel fan-out (`004b`).

As-built at issue start:
- The live path merged artifacts **imperatively** via `_merge_regenerated_artifacts(...)` in `packages/agents/teaching_pack/nodes.py` — preserving **insertion/arrival order**.
- The legacy `merge_artifacts` reducer (`packages/agents/state.py`, on the **unused** `OhMyClassState`) also deduped by **arrival order**.
- The live `TeachingPackState` had **no** `Annotated[..., reducer]` channels at all.

Current state after ADR-020: artifact-level generation uses Send by default with reducer-backed `artifact_chunks` and `artifact_workflow_states`; the old node-local `_merge_regenerated_artifacts` wrapper is removed.

Under `Send` fan-out, sections/dimensions complete in nondeterministic order, so any arrival-order merge is **non-reproducible and untestable**. Build the fix now so `004b` can land cleanly.

- Define a `stable_merge` reducer keyed on a **stable index** (`section_index` / `artifact_id` / `dimension`), not arrival: sort deterministically by the key, dedup by id, then concatenate. Identical output regardless of completion order.
- Attach via `Annotated[list[...], stable_merge]` on the channel(s) that will be written concurrently (artifacts during per-section fill; judge results during per-dimension review).
- Preserve existing **scoped-regeneration** semantics (drop rejected items + append fresh) but express them deterministically (the rejected-then-regenerated set must merge identically under any order).

## Acceptance criteria

- [ ] A reducer keyed on a stable index (not arrival order) exists and is attached to the parallel-written channel(s) on `TeachingPackState`.
- [ ] Out-of-order concurrent writes merge to an **identical** result (property test over permutations).
- [ ] Existing scoped-regeneration behavior (drop rejected + append fresh, preserve others) is preserved and deterministic.
- [ ] No regression in the sequential stage flow.

## Detailed test suite

- [ ] `packages/agents/tests/test_reducer_order_stable.py`: permute write order across N runs → identical merged output (deterministic logic, no LLM).
- [ ] `packages/agents/tests/test_reducer_scoped_regen.py`: rejected items dropped, fresh appended, untouched items preserved; result order-independent.
- [ ] Run `uv run pytest packages/agents/tests/test_reducer_*.py -v`.

## Blocked by

None — can start immediately. (Prerequisite of `004b`.)
