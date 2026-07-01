---
title: Teacher-facing partial artifact status
status: done
labels: []
created: 2026-07-01
---

## What to build

Expose per-artifact generation status to teachers and operators so partial generation is actionable instead of a vague whole-run failure.

The graph will now know which artifact passed, failed, is regenerating, or was skipped because a dependency failed. That status should flow into gate payloads, run events, API responses, and the dashboard. Export remains fail-closed when required artifacts are missing or failed.

Teacher-facing error text must be safe and concise: no provider stack traces, secrets, raw prompts, or internal exception details.

## Acceptance criteria

- [x] Content approval gate payload includes per-artifact generation status and safe summaries when generation is partial.
- [x] Run events record status transitions for artifact generation cycles and artifact workflow states.
- [x] API responses used by the dashboard expose artifact status without leaking internal errors.
- [x] Frontend shows passed, regenerating, failed, skipped-due-dependency, and escalated states in a teacher-readable way.
- [x] Export is blocked with a clear teacher-facing reason when required artifacts are missing or failed.

## Detailed test suite

- [x] `services/gateway/tests/test_artifact_partial_status_api.py`: API payload contains per-artifact status and redacted error summaries.
- [x] `packages/agents/tests/teaching_pack/test_content_approval_partial_payload.py`: gate payload includes actionable partial-generation status.
- [x] `apps/web/tests/artifact-status.test.tsx`: dashboard renders failed/skipped/regenerating states and recommended teacher actions.
- [x] `packages/agents/tests/teaching_pack/test_export_blocks_partial_generation.py`: export_finalize fails closed when required artifacts are unavailable.
- [x] Visual QA/manual browser check for the dashboard partial-status surface.

## Blocked by

- `.scratch/artifact-send-fanout/004-scoped-regeneration-parity.md` — completed before this issue.

## Verification

- `uv run pytest packages/agents/tests/teaching_pack/test_content_approval_partial_payload.py packages/agents/tests/teaching_pack/test_export_blocks_partial_generation.py services/gateway/tests/test_artifact_partial_status_api.py -q` → `4 passed`.
- `pnpm --filter @oh-my-class/web test -- tests/artifact-status.test.tsx tests/teaching-pack-gate-bodies-render.test.tsx` → web suite passed.
