---
title: Wire Inverse Thinking into the generation pipeline
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Wire inverse thinking through the existing teaching-pack pipeline so a teacher request or UI override can select the methodology at Blueprint time, carry it through Visual Engine and Content Creator, and produce a canonical pack plus projections for selected artifacts.

This slice should make the feature reachable behind a flag while preserving existing standard teaching-pack behavior.

## Acceptance criteria

- [ ] A feature flag such as `features.inverse_thinking_v1` gates the pipeline path.
- [ ] Blueprint/LessonPlan can select or carry `methodology: inverse_thinking` and structured inverse-thinking payload metadata.
- [ ] Pack Scope can select inverse-thinking-supported artifacts for v1: lesson, worksheet, quiz, and drill.
- [ ] Visual Engine resolves `creative_frame` through a registry/config and records selection rationale.
- [ ] Content generation contract requests a canonical inverse-thinking pack, not independent per-artifact free text.
- [ ] The generated canonical pack is projected into selected artifact content through the methodology package.
- [ ] LLM calls and run events include methodology-specific metadata tags for methodology, creative frame, projection, feature flag, and repair attempt where applicable.
- [ ] Existing non-inverse teaching-pack flows continue to pass their current tests.

## Detailed test suite

- [ ] `packages/agents/tests/test_inverse_thinking_blueprint.py`: Given a teacher request that explicitly asks for inverse thinking, when Blueprint runs with the feature flag enabled, then `methodology: inverse_thinking` and structured payload metadata are present.
- [ ] `packages/agents/tests/test_inverse_thinking_feature_flag.py`: Given the same request with `features.inverse_thinking_v1` disabled, when the pipeline runs, then it fails closed or prompts instead of silently generating an inverse pack.
- [ ] `packages/agents/tests/test_inverse_thinking_pack_scope.py`: Given artifact selections, when Pack Scope runs, then v1 supports lesson, worksheet, quiz, and drill only.
- [ ] `packages/agents/tests/test_creative_frame_resolution.py`: Given `auto` and explicit creative-frame inputs, when Visual Engine runs, then it records a resolved frame ID and selection rationale.
- [ ] `tests/integration/test_inverse_thinking_pipeline.py`: Given mocked LLM responses, when the pipeline reaches Generate, then it stores one canonical pack and derives selected projections through the methodology package.
- [ ] Metadata test: Given any LLM call in the inverse path, when the request body is built, then tags include `methodology:inverse_thinking`, `creative_frame:*`, `feature_flag:inverse_thinking_v1`, and `repair_attempt:*` where applicable.
- [ ] Regression test: Given a standard teaching-pack request, when the flag and inverse controls are absent, then existing standard flow output is unchanged.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/002-methodology-package-and-projections.md
