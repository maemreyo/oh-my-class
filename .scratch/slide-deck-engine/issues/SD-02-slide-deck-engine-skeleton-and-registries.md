---
title: Build SlideDeckEngine skeleton and typed registries
status: ready-for-agent
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

- [ ] `SlideDeckEngine` exposes a small caller interface and hides internal phases, registries, and validators from graph nodes.
- [ ] Engine phases exist as typed, testable modules: input assembly, pedagogical planning, slide architecture planning, layout composition, interaction planning, content materialization, density/accessibility audit, surface readiness, and export packaging readiness.
- [ ] Layout, block, and interaction registries are present with at least one complete fixture path for a valid teaching deck.
- [ ] The engine can generate or assemble a deterministic valid `SlideDeckData` fixture with no real LLM call.
- [ ] Page-count policy and density budget policy exist and are exercised by tests.
- [ ] The engine returns typed validation/healing/scorecard metadata, even if early values are minimal.
- [ ] Package boundaries remain clean: agents do not import from services/apps, and canonical contracts remain in common/contracts.

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
