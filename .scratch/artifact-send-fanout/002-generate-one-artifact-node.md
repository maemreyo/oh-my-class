---
title: LangGraph worker node that generates one artifact
status: done
labels: [done]
created: 2026-07-01
---

## What to build

Create the LangGraph-compatible worker node that can be targeted by `Send`: `generate_one_artifact`.

The node generates exactly one artifact type from a minimal payload. It must not receive or mutate full `TeachingPackState`. It writes only reducer-backed branch outputs: one artifact chunk on success and one workflow state on every expected outcome. It performs generation-local validation only; pack-level quality remains in `render_quality`.

Expected artifact failures become workflow states rather than whole-superstep exceptions. Infrastructure failures still raise.

Build:

- A typed worker payload shape with `run_id`, `artifact_generation_id`, `artifact_type`, `lesson_plan`, `research_brief`, `theme`, `revision_feedback`, and `dependency_artifacts`.
- `generate_one_artifact(payload)` that reuses the existing content-creator prompt/LLM path for a single artifact type.
- Local validation for JSON parse, artifact type match, schema shape, and safe error summaries.
- Workflow state transitions for queued/running/passed/failed/skipped/escalated where applicable.
- Unit tests using deterministic stubs for the LLM boundary; no graph wiring yet.

## Acceptance criteria

- [x] `generate_one_artifact` can be registered as a graph node and invoked with a single-artifact payload.
- [x] On success it returns `artifact_chunks: [artifact]` tagged with the current generation id and `artifact_workflow_states: [passed_state]`.
- [x] On expected generation failure it returns `artifact_workflow_states: [failed_or_escalated_state]` with a safe, bounded error summary and does not write an artifact chunk.
- [x] It does not write non-branch state keys such as `artifacts`, `quality_scores`, `gate_payload`, or `completed_stages`.
- [x] `render_quality` remains the only pack-level quality authority; branch validation is local only.

## Detailed test suite

- [x] `packages/agents/tests/teaching_pack/test_generate_one_artifact.py`: success returns one current-generation chunk and passed workflow state.
- [x] Same file: malformed JSON/schema mismatch returns failed workflow state without crashing the graph-level caller.
- [x] Same file: artifact type mismatch is treated as expected generation failure.
- [x] Same file: infrastructure/config/cancellation error is not swallowed.
- [x] Existing `packages/agents/tests/sub_agents/test_content_creator_per_artifact.py` still passes.
- [x] LSP diagnostics clean on changed Python files.

## Verification

- 2026-07-01: `uv run pytest packages/agents/tests/teaching_pack/test_generate_one_artifact.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py -q` → `20 passed`.
- 2026-07-01: LSP diagnostics clean for `packages/agents/teaching_pack/generate_one_artifact.py` and `packages/agents/tests/teaching_pack/test_generate_one_artifact.py`.

## Blocked by

- `.scratch/artifact-send-fanout/001-state-and-reducer-foundation.md`
