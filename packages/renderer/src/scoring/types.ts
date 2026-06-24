import type { BaseQuestion } from '../contracts/questions/base.js'

export interface BreakdownItem {
  itemId:  string
  correct: boolean
}

export interface ScoreResult {
  points:        number
  maxPoints:     number
  correctCount?: number
  totalItems?:   number
  breakdown?:    BreakdownItem[]
  feedback?:     string
}

export interface ScoringStrategy<Q extends BaseQuestion = BaseQuestion, R = unknown> {
  score(question: Q, response: R): ScoreResult
}
