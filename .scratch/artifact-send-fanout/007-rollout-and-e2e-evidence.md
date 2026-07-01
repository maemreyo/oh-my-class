---
title: Rollout flag and end-to-end evidence for artifact Send fan-out
status: done
labels: []
created: 2026-07-01
---

## What to build

Make the Send fan-out path safe to release by adding a rollout flag, real graph E2E coverage, failure-injection evidence, and release evidence records.

The rollout must support a fast rollback to the existing imperative artifact workflow until the Send path proves stable. Evidence should cover happy path, scoped regeneration, dependency failure, checkpoint resume, and concurrency caps.

## Acceptance criteria

- [x] A feature flag controls whether the graph uses the Send artifact fan-out path or the existing imperative path.
- [x] Flag-off behavior is byte/shape compatible with the existing artifact workflow tests.
- [x] Flag-on E2E generates a complete pack through the real teaching-pack graph.
- [x] Failure-injection proves one expected artifact failure becomes per-artifact status, not an unexplained whole-run crash.
- [x] Checkpoint/resume evidence proves successful branch results are not duplicated and stale chunks are ignored.
- [x] Release evidence records the scenarios, commands, and artifacts needed for rollout review.

## Detailed test suite

- [x] `tests/e2e/test_artifact_send_fanout_flow.py`: full graph happy path with flag on.
- [x] `tests/e2e/test_artifact_send_scoped_regeneration.py`: teacher scoped rejection regenerates only intended artifact types/dependents.
- [x] `tests/e2e/test_artifact_send_failure_recovery.py`: injected branch failure yields partial status and safe recovery route.
- [x] `tests/e2e/test_artifact_send_checkpoint_resume.py`: interrupted/restarted run resumes without duplicate artifacts.
- [x] Real-surface check: create a teaching-pack run through the gateway and inspect dashboard/API status.
- [x] Release evidence route/file includes pass/fail receipts for all scenarios.

## Blocked by

- `.scratch/artifact-send-fanout/005-concurrency-and-budget-wiring.md` — completed before this issue.
- `.scratch/artifact-send-fanout/006-teacher-facing-partial-status.md` — completed before this issue.

## Verification

- `uv run pytest tests/e2e/test_artifact_send_fanout_flow.py tests/e2e/test_artifact_send_failure_recovery.py tests/e2e/test_artifact_send_checkpoint_resume.py tests/e2e/test_artifact_send_scoped_regeneration.py packages/agents/tests/teaching_pack/test_artifact_generation_state.py packages/agents/tests/teaching_pack/test_artifact_send_graph.py packages/agents/tests/teaching_pack/test_send_scoped_regeneration.py packages/agents/tests/teaching_pack/test_artifact_send_concurrency.py -q` → `20 passed`.
- `uv run pytest services/gateway/tests/test_release_evidence_exports.py::TestReleaseEvidenceExports::test_render_markdown_includes_artifact_send_rollout_receipts -q` → `1 passed`.
- `uv run pytest packages/agents/tests/teaching_pack/test_content_approval_partial_payload.py packages/agents/tests/teaching_pack/test_export_blocks_partial_generation.py services/gateway/tests/test_artifact_partial_status_api.py -q` → `4 passed`.
- Full `services/gateway/tests/test_release_evidence_exports.py` still requires local Postgres on `localhost:5432`; the new artifact Send receipt coverage is DB-free and passed.
