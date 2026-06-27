---
title: Pipeline V2 artifact-level generation workflow
status: review-partial
labels: [pipeline-v2, artifacts, generation, workflow]
created: 2026-06-27
order: 7
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-004-run-contract-setup-stage, ISSUE-005-research-engine, ISSUE-006-adaptive-llm-transport]
adr_refs:
  - docs/adr/008-artifact-workflow-and-rendered-snapshots.md
  - docs/adr/009-quality-healing-and-safety-gates.md
---

## Problem

Current pack-level Content Creator generation is too large, slow, and fragile. V2 needs one artifact per generation unit, explicit workflow state, bounded parallelism, and local retry/healing.

## Scope

Implement the V2 ArtifactOrchestrator and artifact generation workflow.

Agent-ready tasks:

1. Define `ArtifactWorkflowState` contract and persistence mapping.
2. Define artifact generation input contract: artifact type, lesson blueprint, RunContract, ResearchBrief, ArtifactResearchGuidance, visual spec, dependencies.
3. Implement ArtifactOrchestrator with bounded parallelism from RunContract.
4. Generate `lesson`, `worksheet`, `quiz`, and `recap` as individual artifacts.
5. Track per-artifact status, attempts, contract revision id, research guidance id, validation status, judge status, snapshot refs, and last error.
6. Validate each ArtifactContent against schema immediately after generation.
7. Retry only the affected artifact.
8. Split to section-level generation only when artifact size/failure policy requires it.

## Out Of Scope

- Rendered preview UI.
- Non-core artifacts such as drill and infographic.
- Non-HTML exports.

## Acceptance Criteria

- A run can generate core artifacts one at a time.
- One artifact failure does not discard already passed artifacts.
- Artifact statuses are persisted and visible through run status/events.
- Bounded parallelism avoids unbounded 9Router load.
- Malformed JSON retry is scoped to one artifact.
- Core Math and English live 9Router scenarios generate at least one artifact-level output successfully during issue validation.

## Test Plan

- Unit tests for dependency ordering and concurrency limits.
- Contract tests for artifact generation input/output.
- Integration tests with persisted ArtifactWorkflowState.
- Live 9Router smoke for lesson and quiz generation.
- Failure tests for malformed JSON and timeout handling.

## Observability

- Emit events for artifact queued, started, completed, failed, healing started, and healing completed.
- Langfuse metadata includes artifact id/type and contract revision id.

## Required Edge Cases And Tests

- One artifact fails while already-passed artifacts remain valid and are not regenerated.
- Bounded parallelism is respected under 1, 2, and higher configured limits.
- Dependency ordering works when recap depends on lesson summary or quiz depends on objectives.
- Malformed JSON, empty response, schema-invalid response, timeout, and provider error are classified separately.
- Repeated failure splits artifact into smaller unit or escalates according to policy.
- Artifact retry does not duplicate snapshots, events, or workflow attempts after worker retry.
- Teacher feedback scoped to one artifact does not regenerate unrelated artifacts.
- Artifact generation refuses unsupported artifact types in V2 core.
- Artifact output includes required accessibility metadata and no teacher-only answer data in student sections.
- Live 9Router tests cover lesson, worksheet, quiz with why-wrong explanations, and recap.
- Tests verify persisted workflow state after each transition: queued, running, validating, healing, passed, failed, skipped, escalated.

## Rollback

Reduce artifact concurrency to 1 via RunContract/config if provider behavior is unstable. Do not return to pack-level generation for V2.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Artifact workflow and persistence are implemented for core artifacts, but live generation/healing scope is not fully proven.

Evidence:
- Artifact workflow contracts are in `common/contracts/artifact_workflow.py`; persistence mapping is in `services/gateway/pipeline_v2_artifact_models.py` and migration `005_artifact_workflow_state.py`.
- `services/gateway/artifact_workflow.py` implements `ArtifactOrchestrator`, dependency ordering, bounded parallelism, per-artifact retry, schema/quality validation, and unsupported artifact rejection.
- Tests cover dependency ordering, concurrency limit, scoped retry, preserving passed artifacts, quality gate failure, unsupported artifacts, long run IDs, and research guidance in `services/gateway/tests/test_artifact_workflow.py`.
- Persistence round-trip and update behavior are covered in `services/gateway/tests/test_artifact_workflow_persistence.py` and contract tests in `common/contracts/tests/test_artifact_workflow.py`.

Gaps:
- Live 9Router artifact generation for lesson/worksheet/quiz/recap was not found.
- Section-level split-on-size/failure is not proven in the reviewed implementation.
- Repeated failure currently ends in failed state; no verified split-to-section or escalation policy executor was found.
- Error classification is limited to summarized error text, not distinct malformed JSON / timeout / provider error classes.
- Backend routing for teacher feedback scoped to a single artifact was not verified.
