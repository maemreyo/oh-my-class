# Module: schemas

**Path:** `common/schemas`
**Role:** TypeScript types + Zod schemas for the frontend. Auto-generated from `common/contracts/` Pydantic models via `scripts/generate_zod_schemas.py`, with hand-written question type enums.

## Public interface

### Auto-generated Zod schemas (`src/generated/` — 16 modules)
`index.ts` re-exports all generated types and schemas: `ArtifactContent`, `ArtifactDocument`, `AnswerSet`, `ClassProfile`, `ComponentStrategyResult`, `ErrorResponse`, `InverseThinkingPack`, `JudgeOutput`, `LessonPlan`, `LessonSequence`, `METHODOLOGY_REGISTRY`, `QualityReport`, `ResearchBrief`, `RunContract`, `SlideDeckData`, `UnitView`, `VocabularyBatch`, `VocabularyClusterWorkflow`, and all their sub-types.

### Hand-written schemas
- `src/questions.ts` — 50 question type string literals across 5 categories (Core: 12, English: 19, Math/Science: 7, Multimedia: 7, Gamified: 5) + `QuestionTypeSchema` (Zod enum union)
- `src/exercise-types/` — 7 files defining Zod schemas per exercise type:
  - `base.ts` — `BaseQuestionSchema`, `DifficultySchema`, `BloomLevelVNSchema`, `ScoringConfigSchema`, `RubricSchema`, `MetadataSchema`
  - `core.ts` — 12 schemas: `MultipleChoiceSingleSchema`, `TrueFalse4ItemSchema` (with Vietnamese TF scoring), `ShortAnswerSchema`, `EssaySchema`, `FillBlankWordBankSchema`, `ClozeSchema`, `MatchingSchema`, `OrderingSchema`, `DragAndDropSchema`, `DrawingSchema`, `PerformanceSchema`
  - `english.ts` — 19 schemas (vocabulary_scaffolded through passive_voice)
  - `math-science.ts` — 7 schemas (step_by_step_math through financial_literacy)
  - `multimedia.ts` — 7 schemas (multimedia_video through art_project)
  - `gamified.ts` — 6 schemas (timed_challenge through collaborative_activity)
  - `index.ts` — barrel re-export of all exercise-type schemas
- `src/artifact.ts` — **Deprecated** hand-written `ArtifactContentSchema` (replaced by `generated/artifact.ts`)
- `src/lesson_plan.ts` — Legacy `LessonPlanSchema` (replaced by generated version)
- `src/quiz.ts`, `src/run.ts`, `src/error.ts`, `src/log-context.ts` — Hand-written API response types

### Package barrel (`src/index.ts`)
Aggregates all generated + hand-written exports into a single `@oh-my-class/schemas` import path.

## Internal structure

```
common/schemas/
├── package.json                      # @oh-my-class/schemas, deps: zod ^3.23.0
├── src/
│   ├── index.ts                      # Package barrel — all exports
│   ├── questions.ts                  # Hand-written question type enums
│   ├── artifact.ts                   # DEPRECATED — replaced by generated/
│   ├── lesson_plan.ts                # Legacy — replaced by generated/
│   ├── quiz.ts, run.ts, error.ts     # Hand-written API types
│   ├── log-context.ts                # Structured logging types
│   ├── exercise-types/               # 7 files — per-type Zod schemas
│   │   ├── base.ts, core.ts, english.ts, math-science.ts
│   │   ├── multimedia.ts, gamified.ts, index.ts
│   └── generated/                    # Auto-generated from Pydantic (16+ files)
│       ├── index.ts                  # Barrel re-export
│       ├── artifact.ts, artifact_document.ts, artifact_workflow.ts
│       ├── answer_set.ts, class_profile.ts, component_strategy.ts
│       ├── errors.ts, inverse_thinking.ts, judge_output.ts
│       ├── lesson_plan.ts (+ test files), lesson_sequence.ts
│       ├── methodology_registry.ts, quality.ts, research_brief.ts
│       ├── run_contract.ts, slide_deck.ts, unit_view.ts
│       ├── vocabulary_batch.ts, vocabulary_cluster_workflow.ts
```

## Depends on

_None (leaf node)._

| Target | What | Where cited |
|--------|------|-------------|
| **Leaf node** | No outbound imports to other project modules | Verified: `src/index.ts` imports only from internal files and `zod` |
| `zod ^3.23.0` | Runtime dependency (only one) | `package.json:18` |
| `json-schema-to-zod ^2.0.0` | Dev dependency (code generation) | `package.json:20` |

**Phase 3 hypothesis "schemas has no outbound imports to other project modules" — CONFIRMED.** `common/schemas` is a pure leaf node in the dependency graph. It depends only on `zod` at runtime and `json-schema-to-zod` at generation time.

## Used by

- **`web`** — ~32 imports; ArtifactContent, SlideDeckData, SemanticAnchorCluster, InputNormalizationReport
- **`exporters`** — 5 imports; ArtifactContent, SemanticAnchorCluster, PracticeSet

| Consumer | What imported | Where |
|----------|---------------|-------|
| **web** | `Artifact`, `ArtifactContent`, `LessonPlan`, `Run`, `SlideDeckData`, `SlideDeckBlock`, `SemanticAnchorCluster`, `InputNormalizationReport` + 25 more type imports | `apps/web/src/types/index.ts:5-10`, `apps/web/src/components/slide-deck-editor/*.tsx`, `apps/web/src/components/vocabulary-batch-*.tsx` |
| **web (tests)** | `SlideDeckBlockSchema`, `SlideDeckDataSchema`, `SlideDeckInteractionSchema`, `SlideDeckMediaSchema` | Various `.test.ts` files |
| **web (mode-registry)** | `METHODOLOGY_REGISTRY`, `MethodologyMetadata` via **direct path** (bypassing package barrel) | `apps/web/src/components/methodology/mode-registry.ts:1-2` |
| **exporters** | `PracticeSet`, `SemanticAnchorCluster` types | `packages/exporters/` |

## Data & side effects

- **Generation:** `scripts/generate_zod_schemas.py` reads Pydantic JSON Schema → emits Zod files in `src/generated/`
- **Verification:** `scripts/verify_schema_parity.py` and `scripts/verify_frontend_api_contracts.py` enforce parity between Python contracts and TS schemas
- **Test files:** `generated/lesson_plan.test.ts`, `generated/lesson_plan_types.test.ts`, `inverse_thinking.test.ts`, `run.test.ts` — drift-check tests

## Notes / discrepancies vs existing docs

- **`src/artifact.ts` is deprecated** (marked with `@deprecated` JSDoc) — the canonical schema is now `generated/artifact.ts`. Both are re-exported from `index.ts` with the legacy one aliased as `ArtifactContentSchemaLegacy`.
- **`src/lesson_plan.ts` is legacy** — re-exported as `LessonPlanSchemaLegacy` from `index.ts`.
- **The `METHODOLOGY_REGISTRY` is not re-exported** from the package barrel — this forces `web/components/methodology/mode-registry.ts` to use direct relative paths into `common/schemas/src/generated/`. This should be re-exported.
- AGENTS.md §8 lists 16 exercise types per section; the code has 12 core + 19 English + 7 math/science + 7 multimedia + 5 gamified = **50 total** question type string literals.
- The package is `"private": true` (not published to npm) — it's a workspace-only package consumed via TypeScript path aliases.

---
_Traced from source on 2026-07-11. Files examined: all 41 files in common/schemas/src/. Key finding: pure leaf node with zero outbound project imports; METHODOLOGY_REGISTRY missing from barrel re-exports._
