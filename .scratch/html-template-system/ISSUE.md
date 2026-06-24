---
title: "HTML Template System: M2+R2+T3 — File-based Eta Inheritance, Typed Contracts"
status: ready
labels: [architecture, renderer, typescript]
created: 2026-06-24
priority: p0
report: "03"
---

## What to build

Refactor `packages/renderer/` to M2 (full Eta file-based template inheritance) while keeping `renderArtifact()` as the stable public API (R2). Add per-artifact TypeScript contracts assembled into a typed registry (T3).

**Design decisions:**
- **M2**: `base.html` + `pages/*.html` + `components/*.html` — Eta file-based rendering, `eta.renderAsync('pages/quiz', data)`
- **R2**: `renderArtifact()` signature unchanged — internals rewired from direct HTML generation to `eta.renderAsync()`
- **T3**: `contracts/` directory, one file per artifact type, assembled into `ArtifactDataMap` generic registry

## File Structure

```
packages/renderer/
├── src/
│   ├── renderer.ts              # public API — renderArtifact<T>(type, data): Promise<string>
│   ├── eta-engine.ts            # singleton Eta instance, views dir configured
│   ├── contracts/
│   │   ├── index.ts             # ArtifactDataMap + ArtifactType union
│   │   ├── lesson.ts
│   │   ├── quiz.ts
│   │   ├── drill.ts
│   │   ├── worksheet.ts
│   │   ├── recap.ts
│   │   ├── infographic.ts
│   │   ├── answer_key.ts
│   │   ├── flashcard_deck.ts
│   │   ├── reading_passage.ts
│   │   └── exit_ticket.ts
│   ├── sanitizer/               # → sanitizer-module issue
│   ├── theme/                   # → theme-system issue
│   └── preview-server/          # → preview-server issue
└── templates/                   # → template-library issue
```

## Implementation Spec

### `src/eta-engine.ts`

```ts
import { Eta } from 'eta'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export const eta = new Eta({
  views: path.resolve(__dirname, '../templates'),
  cache: process.env.NODE_ENV === 'production',
  autoEscape: true,        // XSS layer 1: Eta auto-escapes by default
  useWith: false,          // all data accessed via `it.` — no scope pollution
})
```

### `src/contracts/index.ts`

```ts
import type { LessonData } from './lesson.js'
import type { QuizData } from './quiz.js'
import type { DrillData } from './drill.js'
import type { WorksheetData } from './worksheet.js'
import type { RecapData } from './recap.js'
import type { InfographicData } from './infographic.js'
import type { AnswerKeyData } from './answer_key.js'
import type { FlashcardDeckData } from './flashcard_deck.js'
import type { ReadingPassageData } from './reading_passage.js'
import type { ExitTicketData } from './exit_ticket.js'

export type ArtifactDataMap = {
  lesson:          LessonData
  quiz:            QuizData
  drill:           DrillData
  worksheet:       WorksheetData
  recap:           RecapData
  infographic:     InfographicData
  answer_key:      AnswerKeyData
  flashcard_deck:  FlashcardDeckData
  reading_passage: ReadingPassageData
  exit_ticket:     ExitTicketData
}

export type ArtifactType = keyof ArtifactDataMap
```

### `src/contracts/quiz.ts` (example)

```ts
export interface MCQuestion {
  id:       string
  prompt:   string
  options:  { label: string; text: string }[]   // label = "A" | "B" | "C" | "D"
  answer:   string                              // correct label — omitted in student render
  explain?: string
}

export interface QuizData {
  title:       string
  subject:     string
  gradeLevel:  string
  timeLimit?:  number           // minutes
  questions:   MCQuestion[]
  theme?:      string           // theme name → ThemeCSSGenerator
  lang?:       string           // default: 'vi'
}
```

### `src/contracts/answer_key.ts` (example)

```ts
import type { MCQuestion } from './quiz.js'

export interface AnswerKeyData {
  title:         string
  subject:       string
  gradeLevel:    string
  questions:     MCQuestion[]  // answers always visible in teacher view
  teachingNotes?: string[]     // per-question notes for the teacher
  rubric?:       string        // scoring guide
  theme?:        string
  lang?:         string
}
```

### `src/renderer.ts` (rewired R2)

```ts
import { eta } from './eta-engine.js'
import type { ArtifactDataMap, ArtifactType } from './contracts/index.js'
import { sanitize } from './sanitizer/index.js'
import { loadTheme } from './theme/loader.js'

export async function renderArtifact<T extends ArtifactType>(
  type: T,
  data: ArtifactDataMap[T],
): Promise<string> {
  const themeCSS = await loadTheme(data.theme ?? 'default')
  const html = await eta.renderAsync(`pages/${type}`, { ...data, themeCSS })
  return sanitize(html, type)   // SA4: sanitize-html pass
}
```

### `src/contracts/lesson.ts` (example)

```ts
export interface LessonSection {
  heading:   string
  body:      string           // markdown or HTML
  components?: string[]       // component HTML snippets to embed
}

export interface LessonData {
  title:       string
  subject:     string
  gradeLevel:  string
  objectives:  string[]       // learning objectives → learning_objective component
  sections:    LessonSection[]
  vocabulary?: VocabEntry[]   // → vocabulary_card components
  theme?:      string
  lang?:       string
}

export interface VocabEntry {
  term:        string
  definition:  string
  partOfSpeech?: string
  example?:    string
}
```

## Tests

```ts
// __tests__/renderer.test.ts

import { renderArtifact } from '../src/renderer.js'
import type { QuizData } from '../src/contracts/quiz.js'

const quizData: QuizData = {
  title: 'Test Quiz',
  subject: 'English',
  gradeLevel: 'Grade 8',
  questions: [{
    id: 'q1',
    prompt: 'What is 2 + 2?',
    options: [
      { label: 'A', text: '3' },
      { label: 'B', text: '4' },
    ],
    answer: 'B',
  }],
}

test('renderArtifact quiz returns valid HTML', async () => {
  const html = await renderArtifact('quiz', quizData)
  expect(html).toContain('<!DOCTYPE html>')
  expect(html).toContain('Test Quiz')
  expect(html).toContain('What is 2 + 2?')
})

test('renderArtifact is generic — wrong contract shape fails TypeScript', () => {
  // @ts-expect-error — missing required fields
  renderArtifact('quiz', { title: 'Only title' })
})

test('all artifact types render without throwing', async () => {
  // smoke test: each type renders with minimal valid data
  const types: ArtifactType[] = ['lesson', 'quiz', 'drill', 'worksheet',
    'recap', 'infographic', 'answer_key', 'flashcard_deck',
    'reading_passage', 'exit_ticket']
  for (const type of types) {
    await expect(renderArtifact(type, minimalData[type])).resolves.toContain('<!DOCTYPE html>')
  }
})
```

## Acceptance Criteria

- [ ] `eta-engine.ts` — singleton Eta, `views` pointed at `../templates`, `autoEscape: true`, `useWith: false`
- [ ] `contracts/` — one file per artifact type (10 files) + `index.ts` registry
- [ ] `ArtifactDataMap` — TypeScript generic maps every artifact type to its data shape
- [ ] `renderArtifact<T>(type, data)` — type-safe, generic, public API unchanged
- [ ] TypeScript compiler catches wrong data shape for a given artifact type
- [ ] All 10 artifact types smoke-test render to valid HTML
- [ ] `eta.renderAsync` used (not `renderString`) — file-based templates
- [ ] `useWith: false` — all template vars accessed via `it.`

## Dependencies

- Blocked by: nothing (standalone renderer module)
- Blocks: `template-library` (templates use this engine), `sanitizer-module` (called from renderer.ts), `theme-system` (loadTheme called from renderer.ts)
- Priority: p0 — first Report 03 issue to implement
