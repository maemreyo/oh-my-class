export type BloomLevel =
  | 'remember'
  | 'understand'
  | 'apply'
  | 'analyze'
  | 'evaluate'
  | 'create'

export type MOETLevel =
  | 'nhan_biet'
  | 'thong_hieu'
  | 'van_dung'
  | 'van_dung_cao'

export type Subject =
  | 'english'
  | 'math'
  | 'science'
  | 'literature'
  | 'history'
  | 'geography'
  | 'informatics'
  | 'all'

export type ExamFormat = 'moet_2025' | 'cambridge' | 'ielts' | 'toefl' | 'general'

export type ScoringType =
  | 'all_or_nothing'
  | 'partial_credit'
  | 'vietnamese_tf_2025'
  | 'rubric'

export interface ScoringConfig {
  type:             ScoringType
  pointsTotal?:     number
  penaltyPerWrong?: number
}

export interface RubricLevel {
  score:       number
  description: string
}

export interface RubricCriterion {
  name:        string
  weight:      number
  levels?:     RubricLevel[]
  descriptors?: Record<'excellent' | 'good' | 'fair' | 'poor', string>
}

export interface Rubric {
  criteria: RubricCriterion[]
}

export interface QuestionMetadata {
  subject:               Subject
  grade:                 number
  topic:                 string
  estimatedTimeSeconds?: number
  lessonId?:             string
  examFormat?:           ExamFormat
}

export interface BaseQuestion {
  id:          string
  type:        string
  difficulty:  BloomLevel
  bloomLevel?: MOETLevel
  tags:        string[]
  metadata:    QuestionMetadata
  scoring?:    ScoringConfig
}
