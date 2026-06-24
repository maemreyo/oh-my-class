import type { BaseQuestion } from '../base.js'

export interface MCOption {
  id:        string
  text:      string
  isCorrect: boolean
}

export interface MultipleChoiceSingle extends BaseQuestion {
  type:         'multiple_choice_single'
  stem:         string
  options:      MCOption[]
  explanation?: string
}

export interface MultipleChoiceMultiple extends BaseQuestion {
  type:         'multiple_choice_multiple'
  stem:         string
  options:      MCOption[]
  explanation?: string
}

export interface TFItem {
  id:     string
  text:   string
  isTrue: boolean
}

// TF 4-item: Vietnamese MOET exam format (QĐ 764/QĐ-BGDĐT)
export interface TrueFalse4Item extends BaseQuestion {
  type:  'true_false_4item'
  stem:  string
  items: [TFItem, TFItem, TFItem, TFItem]
}

export interface PhonicsItem {
  words:        string[]
  correctIndex: number
  reason:       string
}

export interface Phonics extends BaseQuestion {
  type:        'phonics'
  subtype:     'sound_identification' | 'letter_sound' | 'blending'
  instruction: string
  items:       PhonicsItem[]
  cefr?:       string
}

export type ChoiceQuestion =
  | MultipleChoiceSingle
  | MultipleChoiceMultiple
  | TrueFalse4Item
  | Phonics
