---
title: Define slide_deck contracts and schema parity
status: in-progress
labels: [slide-deck-engine, contracts, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-040, ADR-041, ADR-042.

## What to build

Create the canonical domain contracts for a native `slide_deck` artifact. The slice should make `slide_deck` a first-class artifact type at the contract level and provide a typed `SlideDeckData` model that downstream engine, renderer, quality, export, and frontend work can depend on.

The contract must model one deck with stable slide/block/interaction IDs, layout identity, source references, teacher-only facilitation, answer-bearing interaction data, reveal/progression metadata, media policy metadata, accessibility fields, and surface/export metadata. It must support student-safe projection by making teacher-only and answer-bearing fields explicit instead of hidden in untyped dictionaries.

This slice does not build generation, rendering, or UI. It proves that the canonical model is valid, generated TypeScript/Zod parity exists, and existing non-slide artifacts remain compatible.

## Acceptance criteria

- [ ] `slide_deck` is present in all canonical Python artifact-type contracts required for run contracts and artifact workflow input.
- [ ] A Pydantic `SlideDeckData` contract exists in the canonical contracts package and validates a representative deck with slides, blocks, interactions, source refs, teacher-only notes, and accessibility metadata.
- [ ] The contract rejects malformed decks: no slides, duplicate slide IDs, duplicate block IDs within a slide, unsupported layout/block/interaction type, missing required media alt text, and answer-bearing interaction data without teacher-only separation metadata.
- [ ] Generated TypeScript/Zod schemas include the new `slide_deck` contract and generated files are not hand-edited.
- [ ] Existing contract tests for current artifact types still pass unchanged.
- [ ] A fixture deck exists under the slide-deck issue fixtures or test fixtures for later renderer/engine slices.

## Todo items

- [ ] Update canonical artifact-type enums and run-contract validation to include `slide_deck`.
- [ ] Add `SlideDeckData` Pydantic models in `common/contracts` with stable IDs, surfaces, source refs, teacher-only data, media, accessibility, and interaction fields.
- [ ] Add validation tests for valid decks and malformed deck rejection cases.
- [ ] Regenerate TypeScript/Zod schemas through the existing generator.
- [ ] Add a representative fixture deck for later engine, renderer, and quality issues.
- [ ] Run contract/schema tests and record any unrelated pre-existing failures.

## Blocked by

None - can start immediately.

## References

- `docs/adr/040-native-slide-deck-artifact-and-engine.md`
- `docs/adr/041-slide-deck-registries-and-interaction-modules.md`
- `common/contracts/artifact.py`
- `common/contracts/run_contract.py`
- `common/contracts/artifact_workflow.py`
- `scripts/generate_zod_schemas.py`

## Implementation notes

- Keep contracts in `common/contracts`; do not define canonical agent-output Pydantic models inside `packages/agents` or `services/gateway`.
- Prefer discriminated unions/enums over arbitrary dictionaries where validation matters.
- If `ArtifactContent.sections` must remain generic, adapt `SlideDeckData` into it explicitly rather than treating generic sections as the source of truth.
- Do not add open-slide or any runtime dependency.
