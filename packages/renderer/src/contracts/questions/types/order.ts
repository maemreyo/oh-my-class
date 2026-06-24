import type { BaseQuestion } from '../base.js'

export interface OrderItem {
  id:              number
  text:            string
  correctPosition: number
}

export interface Ordering extends BaseQuestion {
  type:         'ordering'
  instructions: string
  items:        OrderItem[]
}

export interface TimelineEvent {
  time:  string
  label: string
}

export interface TenseTimelineQuestion {
  stem:          string
  correctAnswer: string
  tense:         string
}

export interface TenseTimeline extends BaseQuestion {
  type:      'tense_timeline'
  events:    TimelineEvent[]
  questions: TenseTimelineQuestion[]
}

export type VocabStage =
  | 'recognition'
  | 'comprehension'
  | 'production_sentence'
  | 'production_paragraph'

export interface VocabStageEntry {
  stage:    VocabStage
  activity: Record<string, unknown>
}

export interface VocabularyScaffolded extends BaseQuestion {
  type:       'vocabulary_scaffolded'
  targetWord: string
  level:      string
  stages:     VocabStageEntry[]
}

export type OrderQuestion = Ordering | TenseTimeline | VocabularyScaffolded
