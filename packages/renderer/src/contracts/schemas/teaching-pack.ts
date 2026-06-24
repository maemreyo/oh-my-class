import type { LessonPlan, DifferentiationGuide } from './lesson-plan.js'
import type { Worksheet } from './worksheet.js'
import type { FullInfographic } from './infographic.js'
import type { CurriculumStandard } from '../curriculum-standard.js'
import type { QuizData } from '../quiz.js'
import type { FlashcardDeckData } from '../flashcard_deck.js'
import type { RecapData } from '../recap.js'
import type { AnswerKeyData } from '../answer_key.js'

// QG2: Dual quality scoring system
export interface TechnicalScore {
  format:       number   // 0-100: HTML valid, all sections present (weight: 15%)
  content:      number   // 0-100: accuracy, completeness, no hallucinations (weight: 55%)
  presentation: number   // 0-100: readability, visual clarity (weight: 30%)
  total:        number   // weighted: 15% format + 55% content + 30% presentation
}

export interface PedagogicalScore {
  clarity:      number   // 1-5: clear and understandable
  integrity:    number   // 1-5: all required sections present
  depth:        number   // 1-5: beyond surface-level coverage
  practicality: number   // 1-5: teacher can implement as-is
  pertinence:   number   // 1-5: relevant to stated objectives
  total:        number   // average of 5 dimensions
}

export interface QualityScore {
  technical:   TechnicalScore
  pedagogical: PedagogicalScore
  // passed: technical.total >= 70 AND pedagogical.total >= 3.5
  passed:      boolean
  generatedAt: string   // ISO 8601
}

// TP1: teaching_pack = artifact type 11 in ArtifactDataMap
export interface TeachingPackData {
  id:         string
  title:      string
  subject:    string
  gradeLevel: number[]
  duration:   number   // minutes
  language:   'vi' | 'en' | 'bilingual'

  // Core artifacts
  lessonPlan:  LessonPlan
  worksheets:  Worksheet[]
  quizzes:     QuizData[]

  // Supplementary
  vocabularyCards: FlashcardDeckData
  infographics:    FullInfographic[]
  recapContent:    RecapData
  answerKeys:      AnswerKeyData[]

  // Teacher resources
  teachingNotes:   string
  differentiation?: DifferentiationGuide   // DF2: optional addon

  // Standards & quality
  standards:     CurriculumStandard[]
  qualityScore:  QualityScore
  humanReviewed: boolean
}
