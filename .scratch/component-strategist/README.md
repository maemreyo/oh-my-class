# component-strategist — issue set

Production-ready plan for a closed-loop Component Strategist that makes lesson architecture smart, explainable, reproducible, and teacher-trustworthy. Local tracking only; no code implemented in this issue set.

Guiding principle: production-ready rebuild over prompt patches. The strategist chooses pedagogical learning moves and typed renderable components before content generation. Content Creator fills selected components; it does not own component architecture.

## ADRs

- `docs/adr/035-component-strategist-stage.md`
- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `docs/adr/037-component-strategy-fallback-and-feedback-conflicts.md`
- `docs/adr/038-component-strategy-validators-and-release-gates.md`
- `docs/adr/039-component-strategy-blueprint-and-delivery-semantics.md`

## Locked decisions

- Two-pass strategy flow: `provisional_component_strategy` after `planning_blueprint`, then research, then `finalize_component_strategy` before teacher approval.
- One core engine with `provisional` and `final` request modes; no duplicated selectors.
- Core output is a move-centric learning sequence with artifact/export projections.
- YAML source of truth + generated SQLite runtime index.
- Build-time SQLite generation; runtime read-only load; CI freshness check.
- Global knowledge manifest version + per-entry semantic versions.
- Knowledge lifecycle: production, draft, deprecated; deprecated replays old snapshots but is not new-selectable.
- First-class negative rules/contraindications with build-time conflict detection.
- Immutable finalized `ComponentStrategyPlan` snapshot per run plus append-only revisions.
- Deterministic selector authority; optional cacheable LLM rationale/tie-break only.
- Hard-filter-first scoring; scores compare only eligible candidates.
- Typed `ResearchSignals`; no raw research prose in selector scoring.
- Renderer capability manifest is the selector's only renderer-facing dependency.
- Teacher feedback is typed and applies bounded soft multipliers only.
- Content Creator fills/adapts/grounds selected components.
- No silent component substitution, move reordering, or prose-only downgrade by Content Creator.
- Pre-generation strategy gate and post-generation component-fill gate.
- Explicit reviewed fallback graph; no runtime nearest-neighbor fallback guessing.
- Engine-authored teacher feedback conflicts and materiality classification.
- Generic slot validator plus per-learning-move/component validators through plugin registries.
- Safe slot lineage in artifact metadata and rendered HTML `data-*` markers.
- Stable system-owned objective IDs/revisions; strategy snapshots reference blueprint/objective revisions.
- Explicit delivery context, assessment intent, prerequisite readiness, teacher load, and slot budgets.
- Strategy owns slot intent/constraints; Content Creator owns concrete wording/items/answers/rubrics.
- Standalone selector core with thin LangGraph adapter and CLI smoke surface.
- Single blueprint/strategy approval after final strategy; provisional strategy is internal/research-guiding.
- Blueprint approval UX included in v1 with compact rationale and progressive details.
- No full component editor, admin YAML UI, student-outcome learning, RL, or SHAP in v1.

## Issue groups

**Foundation:** CS-01 contracts/snapshots · CS-02 YAML+SQLite knowledge base · CS-03 selector/scorer/diversity core.

**Runtime integration:** CS-04 LangGraph stage + feature flag · CS-05 Content Creator consumes strategy · CS-06 quality gates + observability.

**Teacher experience:** CS-07 blueprint approval strategy panel + typed feedback.

**Production proof:** CS-08 golden scenarios + CLI smoke + end-to-end verification.

**Governance extensions:** CS-09 fallback graph · CS-10 knowledge lifecycle/versioning · CS-11 cache/privacy/observability retention.

**Semantics extensions:** CS-12 blueprint/objective lineage · CS-13 delivery/assessment/budget/slot contracts.

## Suggested execution order

1. CS-01, then CS-02, then CS-03.
2. CS-04 can start after CS-01 and CS-03 interfaces stabilize; it must wire both provisional and final strategy passes.
3. CS-05 depends on CS-03/CS-04.
4. CS-06 starts after CS-03 and finishes after CS-05.
5. CS-07 depends on CS-04 plan payload shape and feedback contracts from CS-01.
6. CS-09 depends on CS-02/CS-03 and should land before CS-05/CS-06 rely on fallback semantics.
7. CS-10 extends CS-02 and should land before broad YAML authoring.
8. CS-11 depends on CS-03/CS-06 and should land before production rollout.
9. CS-12 depends on CS-01/CS-04 and should land before final approval UX hardens.
10. CS-13 depends on CS-01/CS-03/CS-05 and should land before Content Creator integration is considered complete.
11. CS-08 depends on all prior issues and is the release gate.
