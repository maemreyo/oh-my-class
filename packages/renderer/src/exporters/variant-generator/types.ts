import type { BaseQuestion } from '../../contracts/questions/base.js'

export interface TopicConfig {
  name:  string
  count: number
}

export interface VariantConfig {
  totalQuestions: number
  topics:         TopicConfig[]
  variantCount:   number
  seed:           number
}

export interface QuestionBankEntry extends BaseQuestion {
  topic: string
}

export interface ExamVariant {
  variantId:  string
  seed:       number
  questions:  QuestionBankEntry[]
  coverage:   Record<string, number>
}
