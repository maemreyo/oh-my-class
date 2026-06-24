---
title: "Educational Content Research: Schemas, Quality Gates, Export Formats, Pedagogical Backbone"
status: ready
labels: [architecture, schema, education, quality, export]
created: 2026-06-24
priority: p0
report: "07"
---

## What to build

Core content schemas and supporting systems derived from research synthesis (Report 07).
Covers lesson plan structure (UbD + Gagné), TeachingPack bundle, dual quality scoring,
multi-format export, bilingual support, age-appropriate filtering, and diagram rendering.

**Design decisions:**
- **PB3**: UbD macro (Stage 1/2/3) + Gagné micro (9 events in lessonPhases[]) — complementary, not competing
- **TP1**: `teaching_pack` = artifact type 11 in `ArtifactDataMap` — bundle of independently renderable artifacts
- **QG2**: Two scoring systems — G-Eval technical (automated) + 5-dimension pedagogical (LLM judge f.pro)
- **EF4**: All export formats — GIFT, H5P, Google Forms API, QTI (Report 06), Flashcard TSV (Quizlet+Anki), Anki .apkg
- **BL2**: Configurable `language: 'vi' | 'en' | 'bilingual'` per artifact request
- **AF4**: Grade-aware prompt injection (preventive) + `ReadabilityChecker` (detective) — no extra LLM calls
- **CS2**: Typed `CurriculumStandard` interface — agent-generated, no external database
- **WC2**: WCAG 2.2 AA — upgrade from 2.1 AA (Report 03 templates need 3 additions)
- **WB1**: Full `WorksheetBlock` discriminated union — 11 variants including print-specific blocks
- **DF2**: Differentiation guides optional addon — `differentiation?: DifferentiationGuide`, separate prompt section
- **DG3**: Infographic diagrams — LLM generates SVG text, renderer sanitizes + embeds inline; libs via server-side render only (e.g. `@mermaid-js/mermaid-node` if needed)

## File Structure

```
contracts/
├── artifact-data-map.ts          # Add teaching_pack (type 11) + update language field
├── curriculum-standard.ts        # CurriculumStandard, CurriculumFramework enum
└── schemas/
    ├── teaching-pack.ts          # TeachingPackData, QualityScore, DifferentiationGuide
    ├── lesson-plan.ts            # LessonPlan: UbD Stage 1/2/3 + Gagné LessonPhase[]
    ├── worksheet.ts              # Worksheet, WorksheetSection, WorksheetBlock union
    └── infographic.ts            # Infographic, InfographicSection, ColorTheme, DiagramData

packages/
├── agents/
│   └── quality/
│       ├── __init__.py
│       ├── readability_checker.py     # AF4: Flesch-Kincaid grade level check
│       ├── age_band.py                # ACIF age bands config per grade range
│       └── pedagogical_scorer.py     # QG2: 5-dimension rubric via f.pro LLM
└── renderer/
    ├── src/
    │   └── diagrams/
    │       ├── index.ts               # DiagramRenderer: render(data) → SVG string
    │       └── svg-sanitizer.ts       # sanitize LLM-generated SVG (reuse sanitizer-module allowlist)
    └── exporters/
        ├── gift/
        │   └── index.ts               # GIFTExporter → .txt Moodle format
        ├── h5p/
        │   ├── index.ts               # H5PExporter → .h5p ZIP
        │   ├── content-types/
        │   │   ├── multi-choice.ts    # H5P.MultiChoice
        │   │   ├── blanks.ts          # H5P.Blanks
        │   │   ├── true-false.ts      # H5P.TrueFalse
        │   │   ├── flashcards.ts      # H5P.Flashcards
        │   │   └── summary.ts         # H5P.Summary
        │   └── packager.ts            # ZIP builder: h5p.json + content/ + libraries/
        ├── google-forms/
        │   ├── index.ts               # GoogleFormsExporter → batchUpdate payload
        │   ├── auth.ts                # OAuth 2.0 flow (one-time setup)
        │   ├── question-mapper.ts     # QuestionType → Forms API item
        │   └── client.ts             # Forms REST API client
        ├── flashcard-tsv/
        │   └── index.ts               # FlashcardTSVExporter → .txt tab-separated (Quizlet + Anki)
        └── anki-apkg/
            └── index.py               # AnkiApkgExporter → .apkg via genanki
```

## Implementation Spec

### `contracts/schemas/lesson-plan.ts`

```ts
import type { CurriculumStandard } from '../curriculum-standard.js'
import type { BloomLevel, MOETLevel } from './questions/base.js'

// UbD Stage 1 — Desired Results
export interface DesiredResults {
  learningObjectives:      LearningObjective[]
  essentialQuestions:      string[]
  enduringUnderstandings:  string[]
  knowledge:               string[]    // "Students will know..."
  skills:                  string[]    // "Students will be able to..."
}

export interface LearningObjective {
  id:          string
  text:        string
  bloomLevel:  BloomLevel
  moetLevel?:  MOETLevel
  standard?:   CurriculumStandard
}

// UbD Stage 2 — Evidence
export interface AssessmentEvidence {
  performanceTasks:     PerformanceTask[]
  otherEvidence:        string[]   // quizzes, observations, journals
}

export interface PerformanceTask {
  goal:      string   // GRASPS: Goal
  role:      string   // Role
  audience:  string   // Audience
  situation: string   // Situation
  product:   string   // Product/Performance
  standards: string   // Success criteria
}

// UbD Stage 3 — Learning Plan (Gagné 9 Events)
export type GagneEvent =
  | 'gain_attention'
  | 'inform_objectives'
  | 'recall_prior'
  | 'present_content'
  | 'provide_guidance'
  | 'elicit_performance'
  | 'provide_feedback'
  | 'assess_performance'
  | 'enhance_retention'

export interface LessonPhase {
  event:        GagneEvent
  title:        string
  duration:     number          // minutes
  description:  string
  activities:   string[]
  materials?:   string[]
}

// Full LessonPlan
export interface LessonPlan {
  id:          string
  title:       string
  subject:     string
  topic:       string
  gradeLevel:  number[]         // [10, 11] for mixed grades
  duration:    number           // total minutes
  language:    'vi' | 'en' | 'bilingual'
  standards:   CurriculumStandard[]
  prerequisites: string[]

  // UbD 3 stages
  stage1:      DesiredResults
  stage2:      AssessmentEvidence
  stage3: {
    phases:    LessonPhase[]    // Gagné 9 events — all 9 must be present
  }

  // Resources
  materials:   string[]
  vocabulary:  VocabularyTerm[]

  // Optional addon (DF2)
  differentiation?: DifferentiationGuide
}

export interface DifferentiationGuide {
  forStruggling: string[]   // scaffolds, simplified tasks, visual supports
  forAdvanced:   string[]   // extensions, higher Bloom, cross-subject
  forELL:        string[]   // bilingual glossary, sentence frames, visual cues
}

export interface VocabularyTerm {
  term:        string
  definition:  string
  example?:    string
  imageUrl?:   string   // data URI only — standalone HTML contract
}
```

### `contracts/schemas/worksheet.ts`

```ts
import type { QuestionType } from './questions/index.js'

export interface Worksheet {
  id:           string
  title:        string
  instructions: string
  language:     'vi' | 'en' | 'bilingual'
  sections:     WorksheetSection[]
  metadata: {
    difficulty:           number      // 1-5
    estimatedTime:        number      // minutes
    answerKeyIncluded:    boolean
    skillsPracticed:      string[]
    printOptimized:       boolean     // triggers print-specific CSS
  }
}

export interface WorksheetSection {
  id:           string
  type:         'instruction' | 'example' | 'practice' | 'challenge' | 'review'
  title:        string
  instruction?: string
  blocks:       WorksheetBlock[]
}

export type WorksheetBlock =
  | { type: 'text';            content: string }
  | { type: 'question';        question: QuestionType }
  | { type: 'table';           headers: string[]; rows: string[][] }
  | { type: 'blank_lines';     count: number; label?: string }
  | { type: 'space_for_work';  height: number }           // px — print scratch area
  | { type: 'fill_in_table';   headers: string[]; rows: (string | null)[][] }
  | { type: 'matching_lines';  pairs: Array<{ left: string; right: string; blank: boolean }> }
  | { type: 'diagram_space';   instructions: string }     // "Draw your answer here"
  | { type: 'code_block';      language: string; code: string }
  | { type: 'media';           platforms: SubmissionPlatforms }
  | { type: 'svg';             svgContent: string }       // sanitized inline SVG
```

### `contracts/schemas/teaching-pack.ts`

```ts
import type { LessonPlan } from './lesson-plan.js'
import type { Worksheet } from './worksheet.js'
import type { QuizData } from '../artifact-data-map.js'

export interface QualityScore {
  technical: {
    format:       number   // 0-100: HTML valid, all sections present
    content:      number   // 0-100: accuracy, completeness, no hallucinations
    presentation: number   // 0-100: readability, visual clarity
    total:        number   // weighted: 15% format / 55% content / 30% presentation
  }
  pedagogical: {
    clarity:      number   // 1-5: clear and understandable
    integrity:    number   // 1-5: all required sections present
    depth:        number   // 1-5: beyond surface-level coverage
    practicality: number   // 1-5: teacher can implement as-is
    pertinence:   number   // 1-5: relevant to stated objectives
    total:        number   // average of 5 dimensions
  }
  passed:      boolean     // technical.total >= 70 AND pedagogical.total >= 3.5
  generatedAt: string      // ISO 8601
}

export interface TeachingPackData {
  id:             string
  title:          string
  subject:        string
  gradeLevel:     number[]
  duration:       number
  language:       'vi' | 'en' | 'bilingual'

  // Core artifacts
  lessonPlan:     LessonPlan
  worksheets:     Worksheet[]
  quizzes:        QuizData[]

  // Supplementary
  vocabularyCards: FlashcardDeckData
  infographics:    InfographicData[]
  recapContent:    RecapData
  answerKeys:      AnswerKeyData[]

  // Teacher resources
  teachingNotes:   string
  differentiation?: DifferentiationGuide   // DF2: optional addon

  // Standards & quality
  standards:       CurriculumStandard[]
  qualityScore:    QualityScore
  humanReviewed:   boolean
}
```

### `contracts/curriculum-standard.ts`

```ts
export type CurriculumFramework =
  | 'moet_gdpt_2018'          // Thông tư 32/2018/TT-BGDĐT
  | 'moet_decision_3439'      // Quyết định 3439/QĐ-BGDĐT (AI framework)
  | 'moet_circular_02_2025'   // Thông tư 02/2025 (Digital Competence)
  | 'ccss_math'               // Common Core State Standards — Math
  | 'ccss_ela'                // Common Core State Standards — ELA
  | 'cambridge'               // Cambridge International
  | 'ielts'
  | 'custom'

export interface CurriculumStandard {
  framework:    CurriculumFramework
  code:         string          // e.g. "10-Toan-2.3.a", "CCSS.MATH.6.RP.A.1"
  description:  string          // human-readable
  grade?:       number
  subject?:     string
}
```

### `packages/agents/quality/age_band.py`

```python
"""ACIF age band config for grade-aware prompt injection (AF4)."""
from __future__ import annotations
from dataclasses import dataclass
from packages.contracts.questions.base import BloomLevel


@dataclass(frozen=True)
class AgeBand:
    label:                  str
    grade_range:            tuple[int, int]   # inclusive
    max_lexile:             int               # Lexile measure
    max_words_per_sentence: int
    bloom_ceiling:          BloomLevel        # max Bloom level allowed
    sensitive_topic_tier:   int               # ACIF tier 1-4


AGE_BANDS: list[AgeBand] = [
    AgeBand('Early Childhood',   (0, 0),   200,  8,  'understand', 1),
    AgeBand('Lower Primary',     (1, 3),   400,  12, 'understand', 1),
    AgeBand('Upper Primary',     (4, 5),   700,  18, 'apply',      2),
    AgeBand('Lower Secondary',   (6, 9),   1000, 22, 'analyze',    2),
    AgeBand('Upper Secondary',   (10, 12), 1300, 28, 'evaluate',   3),
    AgeBand('Pre-Tertiary',      (13, 13), 1600, 35, 'create',     4),
]


def get_age_band(grade: int) -> AgeBand:
    for band in AGE_BANDS:
        if band.grade_range[0] <= grade <= band.grade_range[1]:
            return band
    return AGE_BANDS[-1]


def build_grade_prompt_section(grade: int) -> str:
    band = get_age_band(grade)
    return f"""
Grade level: Grade {grade} ({band.label})
Vocabulary: max {band.max_lexile} Lexile (keep words simple and grade-appropriate)
Sentence length: max {band.max_words_per_sentence} words per sentence
Bloom ceiling: up to '{band.bloom_ceiling}' level only
Sensitive topics: Tier {band.sensitive_topic_tier} handling required
""".strip()
```

### `packages/agents/quality/readability_checker.py`

```python
"""Flesch-Kincaid grade level readability check (AF4 — detective layer)."""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReadabilityResult:
    fk_grade_level: float
    target_grade:   int
    deviation:      float      # fk_grade_level - target_grade
    passed:         bool       # |deviation| <= MAX_DEVIATION
    warning:        str | None


MAX_DEVIATION = 2.0   # allow ±2 grade levels


def _count_syllables(word: str) -> int:
    word = word.lower().strip(".,!?;:")
    count = len(re.findall(r'[aeiou]+', word))
    if word.endswith('e') and count > 1:
        count -= 1
    return max(1, count)


def check_readability(text: str, target_grade: int) -> ReadabilityResult:
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = text.split()

    if not sentences or not words:
        return ReadabilityResult(0, target_grade, 0, True, None)

    avg_sentence_length = len(words) / len(sentences)
    avg_syllables = sum(_count_syllables(w) for w in words) / len(words)

    # Flesch-Kincaid Grade Level formula
    fk_grade = 0.39 * avg_sentence_length + 11.8 * avg_syllables - 15.59
    deviation = fk_grade - target_grade
    passed = abs(deviation) <= MAX_DEVIATION

    warning = None
    if not passed:
        direction = "too complex" if deviation > 0 else "too simple"
        warning = (
            f"Readability {direction} for Grade {target_grade}: "
            f"FK Grade Level {fk_grade:.1f} (deviation: {deviation:+.1f})"
        )
        logger.warning("Readability check failed", extra={
            "fk_grade_level": fk_grade,
            "target_grade": target_grade,
            "deviation": deviation,
        })

    return ReadabilityResult(fk_grade, target_grade, deviation, passed, warning)
```

### `packages/agents/quality/pedagogical_scorer.py`

```python
"""5-dimension pedagogical quality rubric via f.pro LLM (QG2)."""
from __future__ import annotations
from dataclasses import dataclass
from packages.llm_client.client import LLMClient, ChatMessage
from packages.agents.config import MODELS

SCORE_PROMPT = """You are an expert educational content evaluator.

Score the following educational content on 5 dimensions (1-5 scale each):

1. Clarity (1-5): Is the content clear and understandable for the target audience?
2. Integrity (1-5): Are all required sections present and complete?
3. Depth (1-5): Does it go beyond surface-level coverage?
4. Practicality (1-5): Can a teacher implement this as-is without modification?
5. Pertinence (1-5): Is it relevant to the stated learning objectives?

Return ONLY valid JSON:
{{"clarity": N, "integrity": N, "depth": N, "practicality": N, "pertinence": N,
  "rationale": "one sentence per dimension"}}

Content to evaluate:
{content}"""


@dataclass
class PedagogicalScore:
    clarity:      float
    integrity:    float
    depth:        float
    practicality: float
    pertinence:   float
    total:        float    # average
    passed:       bool     # total >= 3.5
    rationale:    str


async def score_pedagogical(
    content: str,
    llm: LLMClient | None = None,
) -> PedagogicalScore:
    llm = llm or LLMClient()
    response = await llm.chat(
        model=MODELS.quality_gate,   # "f.pro"
        messages=[ChatMessage(role="user", content=SCORE_PROMPT.format(content=content[:6000]))],
        agent="pedagogical_scorer",
        task="quality_gate",
        response_format={"type": "json_object"},
    )
    data = json.loads(response.content)
    dims = [data["clarity"], data["integrity"], data["depth"],
            data["practicality"], data["pertinence"]]
    total = sum(dims) / len(dims)
    return PedagogicalScore(
        clarity=data["clarity"], integrity=data["integrity"],
        depth=data["depth"], practicality=data["practicality"],
        pertinence=data["pertinence"], total=total,
        passed=total >= 3.5, rationale=data.get("rationale", ""),
    )
```

### Export formats summary

| Exporter | Output | Target | Notes |
|----------|--------|--------|-------|
| `gift/` | `.txt` | Moodle | Plain text serializer, trivial |
| `h5p/` | `.h5p` ZIP | Interactive LMS | 5 H5P content types, `packager.ts` builds ZIP |
| `google-forms/` | REST calls | Google Classroom | OAuth 2.0 one-time setup, `batchUpdate` API |
| `qti/` | `.xml` ZIP | Universal LMS | 8 family serializers (Report 06) |
| `flashcard-tsv/` | `.txt` tab-sep | Quizlet + Anki | `front\tback\ttags` format |
| `anki-apkg/` | `.apkg` | Anki proper | `genanki` Python library |

### Diagram rendering (DG3)

```ts
// packages/renderer/src/diagrams/index.ts
import { sanitizeSVG } from './svg-sanitizer.js'

export async function renderDiagram(
  data: DiagramData,
  llmClient: { chat: (opts: unknown) => Promise<{ content: string }> },
): Promise<string> {
  const prompt = buildDiagramPrompt(data)
  const response = await llmClient.chat({
    model: 'f.light',
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.0,
  })
  // Sanitize before embedding — SVG allowlist from sanitizer-module
  return sanitizeSVG(response.content)
}
```

If Mermaid or similar needed in future:
```ts
// Server-side render — no client-side JS, works with CSP
import { run } from '@mermaid-js/mermaid-node'
const svg = await run(mermaidSyntax)   // → clean SVG string
```

### WCAG 2.2 AA additions to Report 03 templates (WC2)

```css
/* 2.4.11 Focus Not Obscured — add to base.html */
:target, :focus { scroll-margin-top: 4rem; }

/* 2.5.8 Target Size Minimum — already pass (we have 44×44px from 2.1) */
/* No change needed — 44px > 24px minimum */

/* 3.3.7 Redundant Entry — handled in template logic */
/* Multi-step worksheets must not re-ask student name/grade */
```

Add to `base.html` `<html>` tag: `lang="vi"` default (overridable per artifact).

## Acceptance Criteria

- [ ] `LessonPlan` schema — UbD Stage 1/2/3 with Gagné `lessonPhases[]` (all 9 events represented)
- [ ] `TeachingPackData` — artifact type 11 in `ArtifactDataMap`, `QualityScore` included
- [ ] `QualityScore.passed` — requires `technical.total >= 70 AND pedagogical.total >= 3.5`
- [ ] `WorksheetBlock` — all 11 variants including `blank_lines`, `space_for_work`, `diagram_space`
- [ ] `CurriculumStandard` — typed `CurriculumFramework` enum, no loose strings
- [ ] `language: 'vi' | 'en' | 'bilingual'` — present in all artifact request types
- [ ] `AgeBand` config — 6 bands, `build_grade_prompt_section(grade)` returns correct constraints
- [ ] `check_readability(text, grade)` — Flesch-Kincaid, warns when |deviation| > 2
- [ ] `score_pedagogical(content)` — 5 dimensions, total avg, `passed` = total >= 3.5
- [ ] `GIFTExporter` — exports valid Moodle GIFT format for all choice/text question types
- [ ] `FlashcardTSVExporter` — tab-separated `front\tback\ttags`, importable by Quizlet + Anki
- [ ] `AnkiApkgExporter` — generates valid `.apkg` via `genanki`
- [ ] `H5PExporter` — valid `.h5p` ZIP for 5 content types (MultiChoice, Blanks, TrueFalse, Flashcards, Summary)
- [ ] `GoogleFormsExporter` — OAuth flow documented, `batchUpdate` payload valid
- [ ] `renderDiagram(data)` — LLM generates SVG, `sanitizeSVG()` reuses sanitizer-module SVG allowlist
- [ ] WCAG 2.2 AA: `scroll-margin-top` in base.html, `lang="vi"` default
- [ ] `DifferentiationGuide` — only generated when explicitly requested (DF2)
- [ ] All quality modules independently testable with `MockLLMClient`

## Dependencies

- Blocked by: `llm-client` (pedagogical_scorer uses LLMClient), `sanitizer-module` (SVG allowlist for diagram rendering), `exercise-types-catalog` (QuestionType in WorksheetBlock)
- Blocks: `content-creator-agent` (LessonPlan schema), `template-library` (WorksheetBlock rendering), `quality-gate-nodes` (QualityScore integration)
- Priority: p0 — foundational schemas for all content generation
