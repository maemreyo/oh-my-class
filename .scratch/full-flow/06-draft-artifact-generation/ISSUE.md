---
title: "Full flow 06 - Generate draft teaching artifacts"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

After blueprint approval, run the pack scope, visual engine, research, and content creator path far enough to produce draft artifact JSON for the requested teaching pack. This should replace dummy pass-through nodes with real, testable behavior.

This slice does not need final export files yet. It must produce stored artifact content that later slices can preview and validate.

## Acceptance criteria

- [ ] Pack scope selects artifact types from request/defaults in a deterministic, typed way.
- [ ] Visual engine selects a supported theme/layout token set for each artifact.
- [ ] Research step produces a minimal `ResearchBundle` or explicitly skips when policy allows basic/no external research.
- [ ] Content creator produces schema-valid `ArtifactContent[]` with teacher-only answer keys separated.
- [ ] Generated artifacts are persisted or recoverable from the run state.
- [ ] Run status advances to draft-generated/reviewing after generation.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: pack scope maps input/export intent to artifact types.
- [ ] Unit: visual engine returns only supported themes/tokens.
- [ ] Unit: research result satisfies the selected research policy contract.
- [ ] Unit: generated artifact content validates against Pydantic/Zod contracts.
- [ ] Integration: approve blueprint, run generation with mocked LLM, then run state contains at least one artifact.
- [ ] Integration: answer keys are not present in student-facing artifact sections.
- [ ] Real surface: create + approve a run, then inspect run state showing draft artifacts.

## Blocked by

- Full flow 05 - Blueprint approval and rejection resume graph
