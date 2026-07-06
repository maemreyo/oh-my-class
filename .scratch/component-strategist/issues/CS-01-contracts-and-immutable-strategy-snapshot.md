---
title: Define Component Strategist contracts and immutable snapshots
status: completed
labels: [component-strategist, contracts, testing]
created: 2026-07-05
---

## Parent

ADR-035 and ADR-036.

## What to build

Create the canonical contracts for component strategy requests, learning moves, strategy slots, artifact/export projections, strategy variants, score breakdowns, teacher feedback events, research signals, fallback metadata, append-only revisions, and immutable per-run finalized strategy snapshots. The contracts must make the strategist independently testable and must be suitable for both LangGraph state and frontend blueprint approval payloads.

The core domain shape is:

```text
ComponentStrategyRequest
  mode: provisional | final
  -> ComponentStrategyResult
     -> status: planned | planned_with_fallback | blocked
     -> ComponentStrategyPlan
      -> recommended StrategyVariant
      -> alternative StrategyVariants[]
      -> learning_sequence[]
         -> exact selected component/exercise type
         -> fill requirements and forbidden fill patterns
         -> budgets and accessibility/differentiation intent
      -> artifact_strategies[]
      -> export_projection_status[]
      -> score breakdown
      -> rejection reasons
      -> teacher-facing rationale
```

Every snapshot must include schema/version fields required by ADR-036: `strategy_schema_version`, `knowledge_db_version`, `selector_version`, `scoring_profile_id`, and enough score/rejection data to explain old runs without recomputing against latest knowledge.

## Acceptance criteria

- [x] Pydantic contracts exist in `common/contracts` for request, result, plan, learning sequence, strategy slot, artifact projection, export projection status, variant, score breakdown, fallback metadata, research signals, typed teacher feedback events, strategy revision, and strategy quality score.
- [x] Generated TypeScript/Zod counterparts exist through the existing schema generation path; generated files are not hand-edited.
- [x] Contracts explicitly distinguish teacher-facing rationale from developer/audit score ledger data.
- [x] Contracts encode bounded teacher feedback events, not free-form preference blobs.
- [x] Contracts distinguish canonical move-centric sequence from artifact/export projections, and every canonical move has explicit projection status.
- [x] Contracts include `mode: provisional | final`; provisional results can carry research questions/hypotheses, while final results carry immutable approved snapshot fields.
- [x] Contracts model typed `ResearchSignals`; selector request does not accept raw research markdown/prose.
- [x] Contracts model typed result states (`planned`, `planned_with_fallback`, `blocked`) for domain outcomes instead of nullable ad hoc plans.
- [x] Contracts support append-only strategy revisions with parent lineage and `teacher_reapproval_required` metadata.
- [x] Old-run compatibility is represented: missing `component_strategy_plan` remains valid in existing teaching-pack state until the feature flag is enabled.
- [x] Contract tests cover valid snapshots, invalid unsupported feedback values, missing version fields, and immutability expectations.

## Completion evidence

- Added frozen Pydantic contracts in `common/contracts/component_strategy.py`.
- Exported the contract surface from `common/contracts/__init__.py`.
- Registered schema generation in `scripts/schema_codegen_config.py` and generated `common/schemas/src/generated/component_strategy.ts` plus index exports.
- Added contract tests in `common/contracts/tests/test_component_strategy_contracts.py`.
- Verified with `uv run pytest common/contracts/tests/test_component_strategy_contracts.py` and `uv run python scripts/generate_zod_schemas.py`.

## Blocked by

None - can start immediately.

## References

- `docs/adr/035-component-strategist-stage.md`
- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `common/contracts/artifact.py`
- `common/contracts/components/__init__.py`
- `common/contracts/methodology_registry.py`
- `packages/agents/teaching_pack/nodes.py`
- `scripts/generate_zod_schemas.py`

## Implementation notes

- Keep this as a deep interface: callers should pass one request object and receive one plan object.
- Do not add selector logic here; this issue owns contracts and contract tests only.
- Use additive schema evolution. Breaking changes require an explicit schema version bump and golden fixture update.
