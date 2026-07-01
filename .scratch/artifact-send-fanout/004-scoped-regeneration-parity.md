---
title: Scoped regeneration through the Send pipeline
status: done
labels: [ready-for-agent]
created: 2026-07-01
---

## What to build

Move quality healing and teacher scoped rejection onto the same wave-based `Send` generation pipeline as initial generation.

At issue start, scoped regeneration was imperative: the runtime computed rejected artifact types, called batch `content_creator_node`, then the old merge wrapper preserved accepted artifacts and replaced rejected ones. After this slice, scoped regeneration creates a new `artifact_generation_id`, issues Sends only for the rejected artifact types and required dependent waves, then the fan-in materializer preserves accepted artifacts and merges current-generation chunks.

The current behavior is type-scoped once a rejected artifact is found: rejecting one worksheet regenerates all artifacts of that type. Preserve or explicitly encode that behavior; do not silently narrow it to a single artifact id.

## Acceptance criteria

- [x] Teacher scoped rejection and quality healing both create a new generation cycle and enter the Send coordinator path.
- [x] Accepted artifacts from prior cycles are preserved unless their artifact type is rejected or required for dependency regeneration.
- [x] Rejected artifact types are regenerated through `generate_one_artifact`; no alternate imperative batch path remains active behind the flag.
- [x] The gate payload or internal state clearly records that scoped regeneration is type-scoped, not item-scoped.
- [x] Existing scoped-regeneration behavior is preserved under flag-off mode.

## Detailed test suite

- [x] `packages/agents/tests/teaching_pack/test_send_scoped_regeneration.py`: rejecting quiz regenerates quiz and skips/regenerates recap according to dependency policy, while lesson/worksheet stay preserved.
- [x] Same file: rejecting lesson triggers dependent wave regeneration for worksheet/quiz/drill/recap.
- [x] Same file: stale chunks from previous generation cycles are ignored.
- [x] Existing `packages/agents/tests/test_reducer_scoped_regen.py` still passes or is replaced by equivalent fan-in helper tests.
- [x] LSP diagnostics clean on changed Python files.

## Completion evidence

- Added fresh generation-cycle handling for flag-gated scoped regeneration (`artifact_generation_revision` increments and stale chunks are ignored by generation id).
- Added internal `artifact_regeneration_scope` metadata with `mode: type_scoped` so the Send router preserves type-scoped regeneration intent across branch returns.
- Preserved accepted artifacts and regenerated rejected/dependent artifact types through `generate_one_artifact`; issue `008` later made this Send path default.
- Verified `uv run pytest packages/agents/tests/teaching_pack/test_send_scoped_regeneration.py packages/agents/tests/teaching_pack/test_artifact_send_graph.py packages/agents/tests/teaching_pack/test_generate_one_artifact.py packages/agents/tests/teaching_pack/test_artifact_generation_state.py packages/agents/tests/teaching_pack/test_artifact_workflow_node.py packages/agents/tests/test_reducer_order_stable.py packages/agents/tests/test_reducer_scoped_regen.py -q` → `55 passed`.
- Verified LSP diagnostics clean on changed Python files.

## Blocked by

- `.scratch/artifact-send-fanout/003-wave-router-and-fanin.md`
