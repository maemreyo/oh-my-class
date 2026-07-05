---
title: Make Content Creator fill selected strategy components
status: ready-for-agent
labels: [component-strategist, content-creator, integration]
created: 2026-07-05
---

## Parent

ADR-035.

## What to build

Change Content Creator integration so selected learning moves/components from `ComponentStrategyPlan` drive artifact sections. Content Creator receives the artifact projection plus compact pack context, then fills, adapts, grounds, localizes, and explains selected typed components; it no longer chooses component architecture when a strategy plan is present.

The implementation must preserve planless compatibility while the feature flag rolls out. When a plan exists, prose-only replacement of selected components is invalid unless a typed fallback path is recorded and accepted by the strategy gate.

## Acceptance criteria

- [ ] Content Creator state accepts optional `component_strategy_plan` and maps relevant moves/components into artifact generation prompts or deterministic fill paths.
- [ ] Content Creator receives artifact projection, ordered slots, fill requirements, forbidden fill patterns, budgets, audience policy, quality expectations, and compact pack context; it does not receive full debug/search ledger.
- [ ] Generated `ArtifactContent.sections[].components` include selected component types from the strategy plan for supported slices.
- [ ] Generated artifacts include strategy slot lineage in metadata for selected slots and supporting micro-components.
- [ ] Content Creator may request typed fill failure/fallback with slot ID, original move ID, failure reason, and attempted component; fallback reason is recorded and gate-visible.
- [ ] Content Creator may not silently replace selected components with `paragraph`-only sections when a richer selected component exists.
- [ ] Content Creator may not reorder selected learning moves, alter objective mapping, exceed hard slot budgets, or add arbitrary components outside explicit expansion policy.
- [ ] Supporting micro-components are allowed only when slot expansion policy permits them and must include parent-slot lineage.
- [ ] Student-facing outputs do not include teacher-only fields such as answer keys, rationales, coaching notes, or wrong-reason explanations where policy forbids them.
- [ ] Tests cover vocabulary/language, exam-prep, concept/math-science, fallback, planless compatibility, slot lineage, expansion policy, and no silent prose downgrade.

## Blocked by

- CS-03 selector, scorer, and diversity core.
- CS-04 LangGraph stage and blueprint payload.

## References

- `docs/adr/035-component-strategist-stage.md`
- `packages/agents/sub_agents/content_creator/nodes.py`
- `packages/agents/sub_agents/content_creator/hierarchical.py`
- `packages/agents/sub_agents/content_creator/prompt_contract.py`
- `packages/agents/sub_agents/content_creator/prompts/system.md`
- `common/contracts/artifact.py`
- `packages/renderer/src/agent-component-projection.ts`

## Implementation notes

- This is the SoC pivot: strategy owns architecture; creator owns content fill.
- Keep compatibility while feature flag is off, but add deprecation path for planless/prose-only generation after CS-08 proves the new path.
- Concrete student wording, exact distractors, answers, rubrics, and teacher scripts are downstream generation responsibilities; strategy owns intent and constraints.
