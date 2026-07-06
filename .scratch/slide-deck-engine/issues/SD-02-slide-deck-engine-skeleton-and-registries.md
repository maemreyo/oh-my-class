---
title: Build SlideDeckEngine skeleton and typed registries
status: done
labels: [slide-deck-engine, agents, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-040 and ADR-041.

## What to build

Create the deep module seam for `SlideDeckEngine` behind the Content Creator boundary. A caller should provide one typed engine request built from lesson blueprint, research brief, dependency artifacts, teacher constraints, and revision feedback; the engine should return one typed result containing `SlideDeckData`, validation reports, healing reports, scorecard, and trace metadata.

The first implementation should establish the engine shape and registries, not final creative quality. It must include a deterministic path that can produce a valid fixture deck without calling real LLMs, plus ports for schema-bound LLM proposal/materialization steps to be implemented later.

The module should include first-class registries for layouts, slide blocks, interactions, media policy, deck policy, quality validators, and surface/export capability declarations. Registry entries should be small, typed modules that declare density budgets, supported surfaces, accessibility requirements, print behavior, teacher-only behavior, and fallback behavior.

## Acceptance criteria

- [x] `SlideDeckEngine` exposes a small caller interface and hides internal phases, registries, and validators from graph nodes.
- [x] Engine phases exist as typed, testable modules: input assembly, pedagogical planning, slide architecture planning, layout composition, interaction planning, content materialization, density/accessibility audit, surface readiness, and export packaging readiness.
- [x] Layout, block, and interaction registries are present with at least one complete fixture path for a valid teaching deck.
- [x] The engine can generate or assemble a deterministic valid `SlideDeckData` fixture with no real LLM call.
- [x] Page-count policy and density budget policy exist and are exercised by tests.
- [x] The engine returns typed validation/healing/scorecard metadata, even if early values are minimal.
- [x] Package boundaries remain clean: agents do not import from services/apps, and canonical contracts remain in common/contracts.

## Todo items

- [x] Define the narrow `SlideDeckEngine` request/result interface behind the Content Creator seam.
- [x] Create typed phase modules for input assembly, planning, layout, interactions, materialization, audit, surface readiness, and export readiness.
- [x] Implement initial layout, block, and interaction registries with capability metadata.
- [x] Add deterministic fake/fixture adapter that returns valid `SlideDeckData` without real LLM calls.
- [x] Add page-count and density budget policy tests.
- [x] Verify package import boundaries and focused engine tests.

## Completion notes

- Implemented `packages/agents/slide_deck_engine/` with one public `SlideDeckEngine.generate()` interface and typed request/result models.
- Added internal typed phase modules for input assembly, pedagogy, architecture, layout, interactions, materialization, density/accessibility, surface readiness, and export readiness.
- Added layout/block/interaction registries and page-count/density policies.
- Added deterministic no-LLM generation path returning valid `SlideDeckData` plus validation, healing, scorecard, and trace metadata.
- Verified: `uv run pytest packages/agents/tests/slide_deck_engine/test_engine.py common/contracts/tests/test_slide_deck.py common/contracts/tests/test_artifact_workflow.py` passed with 18 tests.
- Verified: `lsp_diagnostics` clean for `packages/agents/slide_deck_engine` and package-boundary grep found no `services`/`apps` imports.
- Manual surface check: called `SlideDeckEngine().generate(...)` through the public API and observed `slide-deck-manual-sd02 2 1.0 0`.

## Blocked by

- SD-01 slide deck contracts and schema parity.

## References

- `docs/adr/040-native-slide-deck-artifact-and-engine.md`
- `docs/adr/041-slide-deck-registries-and-interaction-modules.md`
- `packages/agents/sub_agents/content_creator/`
- `packages/agents/sub_agents/content_creator/hierarchical.py`
- `packages/agents/sub_agents/content_creator/nodes.py`

## Implementation notes

- Treat `SlideDeckEngine` as a deep module: one narrow interface, many internal modules.
- Do not create a supervisor/Lead Agent runtime surface; content generation stays behind the existing Content Creator seam.
- LLM use must be behind a port and schema-bound. Tests should use deterministic adapters/fakes.
- Avoid large switch chains where a registry module can own capability metadata.
