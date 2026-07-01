---
title: Retire old imperative artifact merge path after Send rollout
status: done
labels: []
created: 2026-07-01
---

## What to build

After the Send fan-out path is proven and enabled, remove stale alternate paths and update documentation so the architecture has one source of truth.

The cleanup should not happen before rollout evidence exists. Until then, old code remains as rollback. Once the Send path is the default, retire or narrow helpers that encode the old imperative batch merge, update docs, and ensure architecture drift checks cover the new topology.

## Acceptance criteria

- [x] The old imperative batch generation path is removed or kept only as an explicitly named rollback path while the flag still exists.
- [x] `_merge_regenerated_artifacts` is deleted, renamed, or reduced to a pure helper used only by fan-in materialization.
- [x] `ArtifactOrchestrator` is either retired, moved to shared planning helpers, or documented as test-only/fallback; no duplicate production orchestrator remains.
- [x] `docs/system/ARCHITECTURE.md`, `.scratch/ROADMAP.md`, and relevant issue docs no longer claim `Send` is merely planned once it is wired.
- [x] Architecture manifest/drift tests include the Send worker node, reducer channels, and feature flag status where practical.

## Detailed test suite

- [x] Existing artifact workflow, scoped regeneration, quality, teacher gate, and export test suites pass with Send path default.
- [x] Search tests or architecture drift tests prove no stale production imports call the old imperative batch path unexpectedly.
- [x] Docs sync test passes after architecture updates.
- [x] Manual cleanup review confirms no duplicate source-of-truth prose remains in `.scratch/agent-interaction/004b` vs this epic.

## Blocked by

- `.scratch/artifact-send-fanout/007-rollout-and-e2e-evidence.md`

## Verification

- `uv run pytest packages/agents/tests/teaching_pack/test_artifact_send_graph.py packages/agents/tests/teaching_pack/test_artifact_send_concurrency.py packages/agents/tests/teaching_pack/test_thread_config.py services/gateway/tests/test_teaching_pack_executor_config.py tests/test_architecture_sync.py -q` → `17 passed`.
- `uv run pytest tests/e2e/test_artifact_send_fanout_flow.py tests/e2e/test_artifact_send_failure_recovery.py tests/e2e/test_artifact_send_checkpoint_resume.py tests/e2e/test_artifact_send_scoped_regeneration.py packages/agents/tests/teaching_pack/test_artifact_generation_state.py -q` → `7 passed`.
- `pnpm --filter @oh-my-class/web test -- tests/teaching-pack-gate-shell.test.tsx tests/artifact-status.test.tsx tests/teaching-pack-gate-bodies-render.test.tsx` → `165 passed`.
