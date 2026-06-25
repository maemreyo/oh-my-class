---
title: "Full flow 06 - Generate draft teaching artifacts"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but generated artifact contract alignment is broken downstream.** Pack scope, visual engine, researcher, and content creator are wired. Content creator validates against `ArtifactContent`, but quality gate 09 currently expects `{type, content}`, so a valid generated artifact fails the next slice.

Known current implementation:

- `packages/agents/nodes/pack_scope.py` filters/defaults artifact types.
- `packages/agents/nodes/visual_engine.py` validates supported themes.
- `packages/agents/sub_agents/researcher` validates `ResearchBundle`.
- `packages/agents/sub_agents/content_creator` validates `ArtifactContent[]`.
- Existing generation integration tests stop after generation and do not prove passage through quality gates.

## Remaining work

- [ ] Coordinate with Issue 08 so generated `ArtifactContent` is the single canonical shape accepted by quality gates, artifact APIs, renderer, and frontend.
- [ ] Ensure answer keys are represented in a teacher-only structure that can be reliably redacted and excluded from student export.
- [ ] Make generation status/read model transition to a documented draft/reviewing status instead of ambiguous `planning`.
- [ ] Persist/recover generated artifacts by stable ids, not only list index fallback ids.
- [ ] Add tests that continue from generation into schema validation to catch contract mismatches.

## Acceptance criteria

- [ ] Pack scope selects artifact types from request/defaults in a deterministic, typed way.
- [ ] Visual engine selects a supported theme/layout token set for each artifact.
- [ ] Research step produces a minimal `ResearchBundle` or explicitly skips when policy allows basic/no external research.
- [ ] Content creator produces schema-valid `ArtifactContent[]` with teacher-only answer keys separated.
- [ ] Generated artifacts are persisted or recoverable from the run state with stable ids.
- [ ] Run status advances to draft-generated/reviewing after generation.
- [ ] Generated artifacts can pass the canonical Layer 1 schema gate from Issue 08.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: pack scope maps input/export intent to artifact types.
- [ ] Unit: visual engine returns only supported themes/tokens.
- [ ] Unit: research result satisfies the selected research policy contract.
- [ ] Unit: generated artifact content validates against Pydantic/Zod contracts.
- [ ] Integration: approve blueprint, run generation with mocked LLM, then run state contains at least one stable-id artifact.
- [ ] Integration: generated `ArtifactContent` passes Layer 1 schema validation.
- [ ] Integration: answer keys are not present in student-facing artifact sections.
- [ ] Real surface: create + approve a run, then inspect run state showing draft artifacts.

## Blocked by

- Full flow 05 - Blueprint approval and rejection resume graph
