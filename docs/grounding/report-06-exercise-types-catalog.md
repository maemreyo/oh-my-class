# Grounding Report: Report 06 — Exercise Types Catalog

**Date**: 2026-06-24  
**Prepared for**: Implementation of Report 06 tickets  
**Source Report**: `docs/reports/core/06-exercise-types-catalog.md` (1797 lines)

---

## 1. Report 06 Summary

**Title**: Comprehensive Exercise Types Catalog  
**Purpose**: Complete catalog of all educational exercise types, special homework formats, and assessment types for the Vietnamese education system (Chương trình GDPT 2018) and English language learning.

### Report Structure (10 Sections)

| Section | Topic | Types |
|---------|-------|-------|
| 1 | Core Assessment Formats | 12 types (MC, TF 4-item, Short Answer, Essay, Cloze, Matching, Ordering, Drag & Drop, Drawing, Performance) |
| 2 | English Language Learning | 19 types (vocabulary, cloze, reading comprehension, grammar, error correction, paraphrase, dialogue, phonics, dictation, translation, idioms, collocation, word analysis, tense timeline, conditionals, reported speech, passive voice) |
| 3 | Math/Science | 7 types (step-by-step CGI math, geometric proof, data interpretation, lab report, measurement, coding, financial literacy) |
| 4 | Multimedia Homework | 7 types (video, audio, photo, experiment, parent-child, field trip journal, art project) |
| 5 | Large-Scale Exam Prep | Question bank architecture, exam variant generation (500-700 questions) |
| 6 | Interactive & Gamified | Timed challenge, streak/reward, leaderboards, adaptive difficulty (Elo-based), branching scenarios, gamification config |
| 7 | Vietnamese Education Requirements | MOET 2025+ exam structure (QĐ 764), Bloom's taxonomy mapping, competency assessment |
| 8 | IMS QTI Standards | QTI v3.0 concept mapping, interaction types |
| 9 | Master Schema | Complete TypeScript union type covering all 44+ exercise types |
| 10 | Artifact Type Matrix | Which exercise types are supported by which artifact (lesson, worksheet, quiz, drill, recap) |

### Key Vietnamese Education Details

- **TF 4-item scoring** (per QĐ 764/QĐ-BGDĐT): 1 correct=0.1đ, 2=0.25đ, 3=0.5đ, 4=1.0đ
- **Difficulty distribution**: nhận biết 40% / thông hiểu 30% / vận dụng 20% / vận dụng cao 10%
- **Bloom mapping**: nhận biết=remember, thông hiểu=understand, vận dụng=apply+analyze, vận dụng cao=evaluate+create

---

## 2. Issues Tagged `report: "06"`

**Only 1 issue found**:

### Issue: Exercise Types Catalog (`exercise-types-catalog`) — P0, `ready`

**Path**: `.scratch/exercise-types-catalog/ISSUE.md`  
**Status**: `ready`  
**Priority**: `p0` (highest)  
**Labels**: `architecture`, `schema`, `typescript`, `education`

**Description**: Comprehensive question type schema system covering 54+ question types grouped into 8 rendering families, with typed registry, QTI v3.0 exporter, MOET scoring strategies, and seeded exam variant generator.

#### Design Decisions

| Code | Decision | Rationale |
|------|----------|-----------|
| **RF1** | 8 rendering families | Types share templates; `question.type` drives variation |
| **QB2** | Question bank schema + JSON/PDF export | No Elo/spaced repetition — LMS responsibility |
| **MM1** | Multimedia = assignment prompt + rubric | Submission via Google Classroom / Seesaw / Teams |
| **GM1** | Template-level gamification only | Streaks/XP/leaderboards are LMS responsibility |
| **QT3** | QTI v3.0 exporter | One serializer per family (`IQTISerializer` interface), 8 files |
| **RG2** | Class-based `QuestionTypeRegistry` | Typed `QueryCriteria`, single source of truth |
| **SC1** | Strategy pattern for scoring | `vietnamese_tf_2025` implements exact MOET formula |
| **BQ2** | Strict `BaseQuestion` | `BloomLevel` / `MOETLevel` / `Subject` literal types; Zod at agent output |
| **EV1** | Deterministic seed-based generator | Reproducible, auditable exam variants |

#### Files to Create

**Contracts** (`contracts/questions/`):
```
contracts/questions/
├── index.ts
├── base.ts           — BaseQuestion interface with literal types
├── registry.ts       — QuestionTypeRegistry class
├── families.ts       — 8 rendering families mapping
├── choice.ts         — MCQ, TF, matching types
├── text-entry.ts     — Short answer, essay types
├── fill-gap.ts       — Cloze, fill-in-blank types
├── match.ts          — Matching types
├── order.ts          — Ordering types
├── open.ts           — Open-ended types
├── interactive.ts    — Drag & drop, interactive types
└── multimedia.ts     — Multimedia homework types
```

**Renderer** (`packages/renderer/src/`):
```
packages/renderer/src/
├── scoring/
│   ├── index.ts
│   ├── types.ts
│   ├── all-or-nothing.ts
│   ├── partial-credit.ts
│   ├── vietnamese-tf-2025.ts    — MOET_SCALE [0, 0.1, 0.25, 0.5, 1.0]
│   └── rubric.ts
├── exporters/
│   ├── qti/
│   │   ├── index.ts
│   │   ├── base.ts
│   │   ├── types.ts
│   │   └── 8 serializer files (one per family)
│   ├── json/
│   │   └── index.ts
│   └── variant-generator/
│       ├── index.ts
│       ├── shuffler.ts          — Mulberry32 PRNG
│       ├── selector.ts          — Per-topic coverage + proportional selection
│       ├── validator.ts
│       └── types.ts
```

#### Acceptance Criteria (12)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `BaseQuestion` — literal types for `BloomLevel`, `MOETLevel`, `Subject` | ✅ **DONE** |
| 2 | 8 `types/*.ts` files — independent and importable per family | ❌ Pending |
| 3 | `QuestionTypeRegistry.query(criteria)` — correct filtering | ❌ Pending |
| 4 | `families.ts` — every type maps to exactly one `RenderingFamily` | ❌ Pending |
| 5 | `vietnamese-tf-2025.ts` — MOET_SCALE `[0, 0.1, 0.25, 0.5, 1.0]` exact | ❌ Pending |
| 6 | `ScoringStrategy` interface — all 4 strategies implement it | ❌ Pending |
| 7 | `IQTISerializer` interface — all 8 family serializers implement it | ❌ Pending |
| 8 | `QTIExporter.export([])` — valid QTI v3.0 XML | ❌ Pending |
| 9 | `deterministicShuffle(items, 42)` — deterministic (tested) | ❌ Pending |
| 10 | `generateVariants(bank, config)` — 24 variants, unique, coverage guaranteed | ❌ Pending |
| 11 | Multimedia templates include submission footer | ❌ Pending |
| 12 | `questionRegistry` singleton auto-populated at module init | ❌ Pending |

#### Dependencies

| Dependency | Status | Report |
|------------|--------|--------|
| `html-template-system` | ✅ **Implemented** | Report 03 |
| `sanitizer-module` | ✅ **Implemented** | Report 03 |

**Blocks**: `content-creator-agent`, `template-library`

---

## 3. Current Codebase State (Relevant to Report 06)

### What Exists (Already Implemented)

| Component | Status | Location | Relevance |
|-----------|--------|----------|-----------|
| **Zod exercise type schemas** | ✅ Complete | `common/schemas/src/exercise-types/` | ~1,000 lines covering core, english, math-science, multimedia, gamified |
| **Base question types** | ✅ Complete | `common/schemas/src/exercise-types/base.ts` | 72 lines — base definitions |
| **Core assessment types** | ✅ Complete | `common/schemas/src/exercise-types/core.ts` | 181 lines — MCQ, TF, etc. |
| **English types** | ✅ Complete | `common/schemas/src/exercise-types/english.ts` | 295 lines — 19 English types |
| **Math/Science types** | ✅ Complete | `common/schemas/src/exercise-types/math-science.ts` | 153 lines — 7 types |
| **Multimedia types** | ✅ Complete | `common/schemas/src/exercise-types/multimedia.ts` | 102 lines — 7 types |
| **Gamified types** | ✅ Complete | `common/schemas/src/exercise-types/gamified.ts` | 106 lines — gamified types |
| **Pydantic contracts** | ✅ Complete | `common/contracts/` | LessonPlan, ArtifactContent, etc. |
| **Renderer contracts** | ✅ Complete | `packages/renderer/src/contracts/` | 10 artifact type Zod schemas |
| **HTML templates** | ✅ Complete | `packages/renderer/templates/` | 10 pages + 21 components |

### What's Missing (Report 06 Scope)

| Component | Status | Impact |
|-----------|--------|--------|
| **`contracts/questions/` directory** | ❌ Not created | No unified question type registry |
| **`QuestionTypeRegistry` class** | ❌ Not created | Agents can't query available types |
| **8 rendering family type files** | ❌ Not created | No family-based organization |
| **Scoring strategies** | ❌ Not created | No automated scoring (especially Vietnamese TF 2025) |
| **QTI v3.0 exporter** | ❌ Not created | No QTI export capability |
| **Variant generator** | ❌ Not created | No exam variant generation |
| **`BaseQuestion` literal types** | ✅ Done | Only 1 of 12 criteria complete |

### Existing Zod Schemas vs Report 06 Requirements

The existing `common/schemas/src/exercise-types/` already defines many exercise types. Report 06 builds **on top** of these:

| Existing Schema | Report 06 Addition |
|-----------------|-------------------|
| `core.ts` (MCQ, TF, etc.) | → Maps to `choice.ts` family |
| `english.ts` (19 types) | → Maps to multiple families |
| `math-science.ts` (7 types) | → Maps to `open.ts` and `interactive.ts` families |
| `multimedia.ts` (7 types) | → Maps to `multimedia.ts` family |
| `gamified.ts` | → Template-level only (GM1 decision) |

**Key insight**: Report 06 doesn't replace existing schemas — it adds:
1. **Registry** — typed query interface for agents
2. **Families** — 8 rendering groups
3. **Scoring** — Vietnamese TF 2025 formula + 3 other strategies
4. **QTI export** — 8 serializers
5. **Variant generator** — deterministic exam variants

---

## 4. Dependencies & Blockers

### Report 06 Internal Dependencies

```
base.ts (✅ done)
    ├── families.ts (8 rendering families)
    ├── registry.ts (QuestionTypeRegistry)
    └── 8 type files (choice, text-entry, fill-gap, match, order, open, interactive, multimedia)
         ├── scoring/ (4 strategies)
         ├── exporters/qti/ (8 serializers)
         └── exporters/variant-generator/
```

### Cross-Report Dependencies

| Report 06 Task | Depends On | Report | Status |
|-----------------|------------|--------|--------|
| `BaseQuestion` types | — | — | ✅ Done |
| Type files | `BaseQuestion` | Report 06 | ✅ Done |
| Registry | Type files | Report 06 | ❌ Pending |
| Scoring strategies | `BaseQuestion` | Report 06 | ❌ Pending |
| QTI exporters | Type files | Report 06 | ❌ Pending |
| Variant generator | Registry | Report 06 | ❌ Pending |
| Multimedia templates | `html-template-system` | Report 03 | ✅ Done |
| Content Creator usage | Registry | Report 06 | ❌ Pending |

### What Blocks Report 06

**Nothing** — dependencies (`html-template-system`, `sanitizer-module`) are already implemented in Report 03.

### What Report 06 Blocks

| Blocked Item | Impact |
|--------------|--------|
| `content-creator-agent` | Can't select appropriate question types |
| `template-library` | Can't render multimedia assignment prompts |
| QTI export capability | No Moodle/LMS integration |

---

## 5. Implementation Plan (Recommended Order)

### Wave 1: Foundation (Types + Families)

1. **Create `contracts/questions/` directory**
2. **Implement `families.ts`** — 8 rendering families mapping
3. **Implement 8 type files** — `choice.ts`, `text-entry.ts`, `fill-gap.ts`, `match.ts`, `order.ts`, `open.ts`, `interactive.ts`, `multimedia.ts`
4. **Verify** — All types importable, each maps to exactly one family

### Wave 2: Registry

1. **Implement `registry.ts`** — `QuestionTypeRegistry` class with `register()`, `query()`, `getFamily()`, `supports()`, `all()`
2. **Implement `QueryCriteria`** — typed filtering interface
3. **Auto-populate singleton** — all types registered at module init
4. **Write tests** — query filtering, family mapping

### Wave 3: Scoring Strategies

1. **Implement `scoring/types.ts`** — `ScoringStrategy` interface
2. **Implement `all-or-nothing.ts`** — binary correct/incorrect
3. **Implement `partial-credit.ts`** — proportional scoring
4. **Implement `vietnamese-tf-2025.ts`** — MOET_SCALE `[0, 0.1, 0.25, 0.5, 1.0]`
5. **Implement `rubric.ts`** — rubric-based scoring for open-ended
6. **Write tests** — each strategy with edge cases

### Wave 4: QTI Exporter

1. **Implement `exporters/qti/base.ts`** — `IQTISerializer` interface
2. **Implement 8 family serializers** — one per rendering family
3. **Implement `exporters/qti/index.ts`** — `QTIExporter.export([])` → valid QTI v3.0 XML
4. **Write tests** — XML validity, interaction types

### Wave 5: Variant Generator

1. **Implement `shuffler.ts`** — `deterministicShuffle` with Mulberry32 PRNG
2. **Implement `selector.ts`** — per-topic coverage + proportional selection
3. **Implement `validator.ts`** — variant uniqueness + coverage checks
4. **Implement `variant-generator/index.ts`** — `generateVariants(bank, config)` → 24 variants
5. **Write tests** — determinism, uniqueness, coverage

### Wave 6: Integration

1. **Update multimedia templates** — add submission footer (Google Classroom, Seesaw, Teams)
2. **Export from `contracts/questions/index.ts`** — all types + registry + families
3. **Final verification** — all 12 acceptance criteria pass

---

## 6. Key Files to Reference

| Purpose | File | Why |
|---------|------|-----|
| Existing exercise type schemas | `common/schemas/src/exercise-types/` | Base types already defined — Report 06 builds on these |
| Zod base types | `common/schemas/src/exercise-types/base.ts` | 72 lines — `BloomLevel`, `MOETLevel` already typed |
| Core types | `common/schemas/src/exercise-types/core.ts` | 181 lines — MCQ, TF definitions |
| English types | `common/schemas/src/exercise-types/english.ts` | 295 lines — 19 English types |
| Renderer contracts | `packages/renderer/src/contracts/` | Zod schemas for artifact types |
| HTML templates | `packages/renderer/templates/` | Where multimedia submission footer goes |
| Report 03 grounding | `docs/grounding/report-03-html-template-skills.md` | Cross-reference for template system |
| AGENTS.md §9 | `AGENTS.md` | Exercise types quick reference table |

---

## 7. Risks & Considerations

| Risk | Mitigation |
|------|------------|
| Existing Zod schemas may not align with `BaseQuestion` | Verify `common/schemas/src/exercise-types/base.ts` matches Report 06's `BaseQuestion` interface |
| 54+ types is a large scope | Implement in waves — registry first, then scoring, then QTI |
| QTI v3.0 compliance is complex | Start with simplest family (choice), validate XML output |
| Vietnamese TF scoring formula must be exact | Reference QĐ 764 directly — formula is `[0, 0.1, 0.25, 0.5, 1.0]` |
| Variant generator determinism | Use Mulberry32 PRNG with fixed seed — test with `seed=42` |
| Multimedia templates need platform-specific footers | Keep generic — list all platforms, let teacher choose |

---

## 8. Verification Checklist

Before starting implementation:

- [ ] Verify `common/schemas/src/exercise-types/base.ts` has `BloomLevel`, `MOETLevel` types
- [ ] Check existing Zod schemas align with Report 06 type families
- [ ] Confirm `html-template-system` and `sanitizer-module` are implemented (Report 03)
- [ ] Review QĐ 764 scoring formula in AGENTS.md §9

After implementation:

- [ ] All 8 type files importable and map to exactly one family
- [ ] `QuestionTypeRegistry.query(criteria)` returns correct types
- [ ] `vietnamese-tf-2025.ts` scoring matches MOET_SCALE exactly
- [ ] All 4 `ScoringStrategy` implementations pass tests
- [ ] `QTIExporter.export([])` produces valid QTI v3.0 XML
- [ ] `deterministicShuffle(items, 42)` is deterministic (tested)
- [ ] `generateVariants(bank, config)` produces 24 unique variants with coverage
- [ ] Multimedia templates include submission footer
- [ ] `questionRegistry` singleton auto-populated at module init
- [ ] All 12 acceptance criteria pass

---

**Last updated**: 2026-06-24  
**Status**: Ready for implementation
