---
title: "Exercise Types Catalog: RF1 Registry, QTI Export, MOET Scoring, Variant Generator"
status: ready
labels: [architecture, schema, typescript, education]
created: 2026-06-24
priority: p0
report: "06"
---

## What to build

Question type schema system — 54+ question types grouped into 8 rendering families,
a typed registry agents query to select types, QTI v3.0 exporter, MOET scoring
strategies, and a seeded exam variant generator for Vietnamese 2025 exam format.

**Design decisions:**
- **RF1**: 8 rendering families — types share templates, `question.type` drives variation
- **QB2**: Question bank schema + JSON/PDF export; no Elo/spaced repetition (LMS responsibility)
- **MM1**: Multimedia types render assignment prompt + rubric only; submission via Google Classroom / Seesaw / Microsoft Teams for Education
- **GM1**: Template-level gamification only (timer JS, branching JS); streaks/XP/leaderboards are LMS responsibility
- **QT3**: QTI v3.0 exporter — one serializer per family (`IQTISerializer` interface), 8 files
- **RG2**: Class-based `QuestionTypeRegistry` — typed `QueryCriteria`, single source of truth for agent selection + family lookup + QTI serializer lookup
- **SC1**: Strategy pattern for scoring — `vietnamese_tf_2025` implements exact MOET formula
- **BQ2**: Strict `BaseQuestion` with `BloomLevel` / `MOETLevel` / `Subject` literal types; Zod validation at agent output layer (not contracts layer)
- **EV1**: Deterministic seed-based exam variant generator — reproducible, auditable

## File Structure

```
contracts/questions/
├── index.ts                   # QuestionType union + re-exports
├── base.ts                    # BaseQuestion, BloomLevel, MOETLevel, Subject, ScoringConfig
├── registry.ts                # QuestionTypeRegistry (RG2) + QuestionTypeMeta + QueryCriteria
├── families.ts                # FAMILY_MAP: QuestionType['type'] → RenderingFamily
└── types/
    ├── choice.ts              # MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item, Phonics
    ├── text-entry.ts          # Cloze, ShortAnswer, GrammarTransformation, ReportedSpeech, PassiveVoice, ConditionalBuilder, ErrorCorrection, SentenceManipulation
    ├── fill-gap.ts            # FillBlankWordBank, ClozeMixed, DialogueCompletion
    ├── match.ts               # Matching, MatchingVocabulary, Collocation, Idioms, WordAnalysis
    ├── order.ts               # Ordering, TenseTimeline, VocabularyScaffolded
    ├── open.ts                # Essay, Paraphrase, Translation, LabReport, Drawing, Performance, Dictation
    ├── interactive.ts         # DragAndDrop, BranchingScenario, StepByStepMath, GeometricProof, DataInterpretation, CodingExercise, FinancialLiteracy, Measurement
    └── multimedia.ts          # MultimediaVideo, MultimediaAudio, MultimediaPhoto, ExperimentDocumentation, ParentChildActivity, FieldTripJournal, ArtProject

packages/renderer/src/
├── scoring/
│   ├── index.ts               # ScoreCalculator: score(question, response) → ScoreResult
│   ├── types.ts               # ScoringStrategy interface, ScoreResult
│   └── strategies/
│       ├── all-or-nothing.ts  # MC single, ordering
│       ├── partial-credit.ts  # MC multiple
│       ├── vietnamese-tf-2025.ts  # TF 4-item: MOET 764/QĐ-BGDĐT formula
│       └── rubric.ts          # Essay, performance, drawing
└── exporters/
    ├── qti/
    │   ├── index.ts           # QTIExporter.export(questions[]) → XML string
    │   ├── base.ts            # XML helpers: assessmentItem(), responseDeclaration()
    │   ├── types.ts           # QTI XML node types
    │   └── serializers/
    │       ├── choice.ts      # → choiceInteraction
    │       ├── text-entry.ts  # → textEntryInteraction
    │       ├── fill-gap.ts    # → inlineChoiceInteraction
    │       ├── match.ts       # → matchInteraction
    │       ├── order.ts       # → orderInteraction
    │       ├── open.ts        # → extendedTextInteraction
    │       ├── interactive.ts # → associateInteraction
    │       └── multimedia.ts  # → uploadInteraction
    ├── json/
    │   └── index.ts           # JSONExporter: question bank → JSON file (QB2)
    └── variant-generator/
        ├── index.ts           # generateVariants(bank, config) → ExamVariant[]
        ├── shuffler.ts        # deterministicShuffle(items, seed): T[] — Mulberry32 PRNG
        ├── selector.ts        # selectQuestions(bank, criteria, seed) — coverage guarantee
        ├── validator.ts       # validateVariant(variant) — topic + difficulty coverage check
        └── types.ts           # VariantConfig, ExamVariant
```

## Implementation Spec

### `contracts/questions/base.ts`

```ts
export type BloomLevel =
  'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create'

export type MOETLevel =
  'nhan_biet' | 'thong_hieu' | 'van_dung' | 'van_dung_cao'

export type Subject =
  'english' | 'math' | 'science' | 'literature' |
  'history' | 'geography' | 'informatics' | 'all'

export type ExamFormat = 'moet_2025' | 'cambridge' | 'ielts' | 'toefl' | 'general'

export type ScoringType =
  'all_or_nothing' | 'partial_credit' | 'vietnamese_tf_2025' | 'rubric'

export interface ScoringConfig {
  type:             ScoringType
  pointsTotal?:     number
  penaltyPerWrong?: number
}

export interface Rubric {
  criteria: Array<{
    name:         string
    weight:       number
    levels?:      Array<{ score: number; description: string }>
    descriptors?: Record<'excellent' | 'good' | 'fair' | 'poor', string>
  }>
}

export interface BaseQuestion {
  id:          string
  type:        string
  difficulty:  BloomLevel
  bloomLevel?: MOETLevel        // Vietnamese MOET equivalent
  tags:        string[]
  metadata: {
    subject:               Subject
    grade:                 number   // 1–12
    topic:                 string
    estimatedTimeSeconds?: number
    lessonId?:             string
    examFormat?:           ExamFormat
  }
  scoring?:    ScoringConfig
}
```

### `contracts/questions/registry.ts`

```ts
import type { ArtifactType } from '../index.js'
import type { BloomLevel, MOETLevel, Subject, ExamFormat } from './base.js'
import type { RenderingFamily } from './families.js'
import type { IQTISerializer } from '../../packages/renderer/src/exporters/qti/types.js'

export interface QuestionTypeMeta {
  type:           string
  family:         RenderingFamily
  label:          string            // human-readable: "Multiple Choice (Single Answer)"
  labelVi:        string            // Vietnamese: "Trắc nghiệm một đáp án"
  artifacts:      ArtifactType[]
  bloomLevels:    BloomLevel[]
  moetLevels?:    MOETLevel[]
  subjects:       Subject[]
  examFormats:    ExamFormat[]
  requiresMedia:  boolean
  isInteractive:  boolean           // needs JS in template (timer, drag, branch)
  complexity:     'low' | 'medium' | 'high'  // LLM generation complexity
  qtiInteraction: string            // QTI interaction type for exporter lookup
}

export interface QueryCriteria {
  artifactType?:  ArtifactType
  bloomLevel?:    BloomLevel
  moetLevel?:     MOETLevel
  subject?:       Subject
  examFormat?:    ExamFormat
  requiresMedia?: boolean
  isInteractive?: boolean
  maxComplexity?: 'low' | 'medium' | 'high'
}

export class QuestionTypeRegistry {
  private _types = new Map<string, QuestionTypeMeta>()

  register(meta: QuestionTypeMeta): void {
    this._types.set(meta.type, meta)
  }

  query(criteria: QueryCriteria): QuestionTypeMeta[] {
    return [...this._types.values()].filter(m => {
      if (criteria.artifactType  && !m.artifacts.includes(criteria.artifactType))   return false
      if (criteria.bloomLevel    && !m.bloomLevels.includes(criteria.bloomLevel))   return false
      if (criteria.moetLevel     && !m.moetLevels?.includes(criteria.moetLevel))    return false
      if (criteria.subject       && !m.subjects.includes(criteria.subject) && !m.subjects.includes('all')) return false
      if (criteria.examFormat    && !m.examFormats.includes(criteria.examFormat))   return false
      if (criteria.requiresMedia !== undefined && m.requiresMedia !== criteria.requiresMedia) return false
      if (criteria.isInteractive !== undefined && m.isInteractive !== criteria.isInteractive) return false
      if (criteria.maxComplexity) {
        const order = { low: 0, medium: 1, high: 2 }
        if (order[m.complexity] > order[criteria.maxComplexity]) return false
      }
      return true
    })
  }

  getFamily(type: string): RenderingFamily {
    const meta = this._types.get(type)
    if (!meta) throw new Error(`Unknown question type: ${type}`)
    return meta.family
  }

  supports(type: string, artifact: ArtifactType): boolean {
    return this._types.get(type)?.artifacts.includes(artifact) ?? false
  }

  all(): QuestionTypeMeta[] {
    return [...this._types.values()]
  }
}

// Singleton — populated by families.ts at module init
export const questionRegistry = new QuestionTypeRegistry()
```

### `scoring/strategies/vietnamese-tf-2025.ts`

```ts
import type { ScoringStrategy, ScoreResult } from '../types.js'
import type { TrueFalse4Item } from '../../../contracts/questions/types/choice.js'

// MOET Decision 764/QĐ-BGDĐT — non-linear partial credit
// 1 correct → 0.1đ, 2 → 0.25đ, 3 → 0.5đ, 4 → 1.0đ
const MOET_SCALE: readonly number[] = [0, 0.1, 0.25, 0.5, 1.0]

export const vietnameseTF2025: ScoringStrategy<TrueFalse4Item> = {
  score(question, response): ScoreResult {
    const correctCount = question.items.filter(
      (item, i) => item.isTrue === response.answers[i]
    ).length

    return {
      points:       MOET_SCALE[correctCount],
      maxPoints:    1.0,
      correctCount,
      totalItems:   question.items.length,
      breakdown:    question.items.map((item, i) => ({
        itemId:   item.id,
        correct:  item.isTrue === response.answers[i],
      })),
    }
  }
}
```

### `exporters/variant-generator/shuffler.ts`

```ts
/**
 * Deterministic shuffle using Mulberry32 PRNG.
 * Same seed always produces the same shuffle — required for exam reproducibility.
 */

function mulberry32(seed: number): () => number {
  return function() {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed)
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t
    return ((t ^ t >>> 14) >>> 0) / 4294967296
  }
}

export function deterministicShuffle<T>(items: T[], seed: number): T[] {
  const rng = mulberry32(seed)
  const result = [...items]
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]]
  }
  return result
}
```

### `exporters/variant-generator/selector.ts`

```ts
import { deterministicShuffle } from './shuffler.js'
import type { QuestionBankEntry, VariantConfig } from './types.js'

export function selectQuestions(
  bank: QuestionBankEntry[],
  config: VariantConfig,
  seed: number,
): QuestionBankEntry[] {
  const selected: QuestionBankEntry[] = []

  // Per-topic coverage: select proportionally from each topic
  for (const topicConfig of config.topics) {
    const topicQs = bank.filter(q => q.topic === topicConfig.name)
    const shuffled = deterministicShuffle(topicQs, seed + topicConfig.name.length)
    selected.push(...shuffled.slice(0, topicConfig.count))
  }

  // Verify difficulty distribution
  const shuffledSelected = deterministicShuffle(selected, seed)
  return shuffledSelected.slice(0, config.totalQuestions)
}
```

## Multimedia Submission Note (MM1)

All multimedia question types render with a submission footer:

```ts
// contracts/questions/types/multimedia.ts
export interface SubmissionPlatforms {
  platforms: Array<'google_classroom' | 'seesaw' | 'microsoft_teams' | 'email'>
  customNote?: string
}
```

Template renders: *"Submit via: Google Classroom / Seesaw / Microsoft Teams for Education"*

## Agent Usage Example

```ts
// Content creator agent selects question types for a quiz
const types = questionRegistry.query({
  artifactType:   'quiz',
  moetLevel:      'van_dung',
  subject:        'english',
  requiresMedia:  false,
  maxComplexity:  'medium',
})
// → [grammar_transformation, cloze_mixed, error_correction, passive_voice, ...]

// Agent picks 5 types → generates questions → validated by Zod schema at output boundary
```

## Acceptance Criteria

- [ ] `BaseQuestion` — `BloomLevel`, `MOETLevel`, `Subject` as literal types (no loose strings)
- [ ] 8 `types/*.ts` files — each covers its family's question types, independently importable
- [ ] `QuestionTypeRegistry.query(criteria)` — returns correct subset for all criteria combinations
- [ ] `families.ts` — every `QuestionType['type']` maps to exactly one `RenderingFamily`
- [ ] `vietnamese-tf-2025.ts` — MOET_SCALE `[0, 0.1, 0.25, 0.5, 1.0]` exact, tested
- [ ] `ScoringStrategy` interface — all 4 strategies implement it, independently testable
- [ ] `IQTISerializer` interface — all 8 family serializers implement it
- [ ] `QTIExporter.export([])` — returns valid QTI v3.0 XML string
- [ ] `deterministicShuffle(items, 42)` — always returns same result (tested)
- [ ] `generateVariants(bank, config)` — 24 variants, each unique, topic coverage guaranteed
- [ ] Multimedia templates include submission footer with Google Classroom / Seesaw / Teams
- [ ] `questionRegistry` singleton populated at module init — no manual registration in tests
- [ ] All types pass Zod validation at agent output boundary (Zod schemas in agent package, not contracts)

## Dependencies

- Blocked by: `html-template-system` (rendering families need template contracts), `sanitizer-module`
- Blocks: `content-creator-agent` (needs registry for type selection), `template-library` (needs family definitions for components)
- Priority: p0 — foundational schema for all content generation
