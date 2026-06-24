import type { CurriculumStandard } from '../curriculum-standard.js'
import type { BloomLevel, MOETLevel } from '../questions/base.js'

// ── UbD Stage 1: Desired Results ─────────────────────────────────────────────

export interface LearningObjective {
  id:         string
  text:       string
  bloomLevel: BloomLevel
  moetLevel?: MOETLevel
  standard?:  CurriculumStandard
}

export interface DesiredResults {
  learningObjectives:     LearningObjective[]
  essentialQuestions:     string[]
  enduringUnderstandings: string[]
  knowledge:              string[]   // "Students will know..."
  skills:                 string[]   // "Students will be able to..."
}

// ── UbD Stage 2: Assessment Evidence ─────────────────────────────────────────

export interface PerformanceTask {
  goal:      string   // GRASPS: Goal
  role:      string   // Role
  audience:  string   // Audience
  situation: string   // Situation
  product:   string   // Product / Performance
  standards: string   // Success criteria
}

export interface AssessmentEvidence {
  performanceTasks: PerformanceTask[]
  otherEvidence:    string[]   // quizzes, observations, journals
}

// ── UbD Stage 3: Learning Plan (Gagné 9 Events) ───────────────────────────────

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
  event:       GagneEvent
  title:       string
  duration:    number     // minutes
  description: string
  activities:  string[]
  materials?:  string[]
}

// ── Full LessonPlan ───────────────────────────────────────────────────────────

export interface VocabularyTerm {
  term:       string
  definition: string
  example?:   string
  imageUrl?:  string   // data URI only
}

export interface DifferentiationGuide {
  forStruggling: string[]   // scaffolds, simplified tasks, visual supports
  forAdvanced:   string[]   // extensions, higher Bloom, cross-subject
  forELL:        string[]   // bilingual glossary, sentence frames, visual cues
}

export interface LessonPlan {
  id:           string
  title:        string
  subject:      string
  topic:        string
  gradeLevel:   number[]   // [10, 11] for mixed grades
  duration:     number     // total minutes
  language:     'vi' | 'en' | 'bilingual'
  standards:    CurriculumStandard[]
  prerequisites: string[]

  // UbD 3 stages
  stage1: DesiredResults
  stage2: AssessmentEvidence
  stage3: {
    phases: LessonPhase[]   // Gagné 9 events — all 9 must be present
  }

  // Resources
  materials:  string[]
  vocabulary: VocabularyTerm[]

  // Optional addon (DF2)
  differentiation?: DifferentiationGuide
}
