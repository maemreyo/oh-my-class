# Module: schemas

**Path:** `common/schemas`
**Role:** TypeScript types + Zod schemas for the frontend. Auto-generated from `common/contracts/` Pydantic models via `scripts/generate_zod_schemas.py`.

## Public interface

- 16 auto-generated Zod schema modules in `src/generated/` (artifact, artifact_workflow, class_profile, component_strategy, errors, inverse_thinking, judge_output, lesson_plan, lesson_sequence, methodology_registry, quality, research_brief, run_contract, slide_deck, unit_view, vocabulary_batch, vocabulary_cluster_workflow)
- 45+ question type enums in `src/questions.ts` (Core: 12, English: 19, Math/Science: 7, Multimedia: 7, Gamified: 5)
- 7 exercise-type Zod schema files in `src/exercise-types/` (base, core, english, math-science, multimedia, gamified, index)
- Re-exports: `src/index.ts` aggregates all generated + hand-written schemas

## Internal structure

- `src/generated/` — Auto-generated from Python Pydantic (16 files)
- `src/questions.ts` — Hand-written question type enums (NOT generated)
- `src/quiz.ts`, `src/run.ts`, `src/error.ts`, `src/log-context.ts` — Hand-written API types
- `src/exercise-types/` — 7 files for per-exercise-type Zod schemas

## Depends on

- **`contracts`** — mirror of Pydantic models (generated from it via `json-schema-to-zod`)
- external: `zod ^3.23.0` (only runtime dep)
- dev: `json-schema-to-zod`, `typescript`, `vitest`

## Used by

- **`web`** — 35 imports (`src/types/index.ts` re-exports)
- **`exporters`** — 10 imports (PracticeSet, SemanticAnchorCluster types)

## Data & side effects

- Generation: `scripts/generate_zod_schemas.py` reads Pydantic JSON Schema → emits Zod
- Verification: `scripts/verify_schema_parity.py` and `scripts/verify_frontend_api_contracts.py` enforce parity

---

_Traced from source on 2026-07-10. Files examined: all 39 files. Key insight: the hand-written question types in `src/questions.ts` are NOT generated and are the source of truth for frontend question type enums._
