---
title: Align artifact workflow support with v1 inverse-thinking artifact scope
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Fix the backend artifact workflow mismatch discovered in `services/gateway/artifact_workflow.py`: `RunContract.ArtifactType` accepts `lesson`, `worksheet`, `quiz`, `drill`, `recap`, and `infographic`, but `ArtifactWorkflow.CoreArtifactType` and `ArtifactOrchestrator` currently support only `lesson`, `worksheet`, `quiz`, and `recap`; `drill` and `infographic` are rejected as unsupported. The inverse-thinking v1 plan explicitly includes `drill`, so the pipeline cannot currently satisfy the accepted v1 scope.

This slice should decide and implement one production path: either add `drill` to the core artifact workflow for v1, or revise inverse-thinking v1 scope to exclude `drill` until a later issue. Prefer adding `drill` because existing renderer contracts already include `DrillData` and `renderAgentArtifact()` supports `drill`.

## Acceptance criteria

- [ ] The accepted inverse-thinking v1 artifact scope matches the backend workflow scope exactly.
- [ ] `ArtifactWorkflow.CoreArtifactType`, dependency planning, state generation, and orchestration either support `drill` or explicitly reject it with a documented v1 deferral and updated issue blockers.
- [ ] If `drill` is supported, dependencies are defined intentionally, not by copying quiz behavior without review.
- [ ] `infographic` remains intentionally unsupported in v1 unless the implementation adds full workflow/research/quality support.
- [ ] Existing standard lesson/worksheet/quiz/recap workflow behavior remains unchanged.
- [ ] Error messages for unsupported artifact types explain the supported set and the reason.

## Detailed test suite

- [ ] `common/contracts/tests/test_artifact_workflow.py`: Given a `RunContract` containing `drill`, when building artifact workflow input, then contract parsing succeeds and artifact workflow type coverage is explicit.
- [ ] `services/gateway/tests/test_artifact_workflow.py`: Given `artifact_types=["lesson", "drill"]`, when `ArtifactOrchestrator.plan()` runs, then the resulting plan includes `drill` with the correct dependency list.
- [ ] `services/gateway/tests/test_artifact_workflow.py`: Given `artifact_types=["drill"]` without required dependencies, when planning runs, then the error names the missing dependency.
- [ ] `services/gateway/tests/test_artifact_workflow.py`: Given `artifact_types=["infographic"]`, when planning runs, then it fails with a typed unsupported-artifact error unless infographic support is deliberately added.
- [ ] Integration test: Given a mocked generator returning lesson and drill artifacts, when `generate_core_artifacts()` runs, then both artifacts reach `passed` state and are returned in dependency order.
- [ ] Regression test: Existing lesson/worksheet/quiz/recap plan ordering remains unchanged.

## Blocked by

- .scratch/inverse-thinking/002-methodology-package-and-projections.md
- .scratch/inverse-thinking/003-pipeline-wiring.md
