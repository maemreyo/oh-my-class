import type { BaseQuestion } from '../base.js'

export interface Cloze extends BaseQuestion {
  type:       'cloze'
  clozeType:  'grammar' | 'vocabulary' | 'contextual'
  passage:    string
  blanks:     Array<{ id: number; correctAnswer: string; hint?: string }>
  caseSensitive: boolean
}

export interface ShortAnswer extends BaseQuestion {
  type:               'short_answer'
  stem:               string
  correctAnswer:      string
  acceptableAnswers:  string[]
  tolerance?:         number | null
  unit?:              string | null
}

export interface GrammarTransformation extends BaseQuestion {
  type:               'grammar_transformation'
  sourceSentence:     string
  expectedAnswer:     string
  acceptableAnswers:  string[]
  grammarPoint:       string
}

export interface ReportedSpeech extends BaseQuestion {
  type:           'reported_speech'
  directSpeech:   string
  expectedAnswer: string
  changes?: Array<{
    from: string
    to:   string
    type: 'pronoun' | 'tense' | 'time' | 'place'
  }>
}

export interface PassiveVoice extends BaseQuestion {
  type:            'passive_voice'
  direction:       'active_to_passive' | 'passive_to_active'
  activeSentence?: string
  passiveSentence?: string
  expectedPassive?: string
  expectedActive?:  string
  tense:           string
}

export interface ConditionalActivity {
  subtype:         'completion' | 'transformation' | 'identification'
  stem?:           string
  sourceSentence?: string
  correctAnswer:   string
  conditionalType: string
}

export interface ConditionalBuilder extends BaseQuestion {
  type:         'conditional_builder'
  conditionals: Array<'type0' | 'type1' | 'type2' | 'type3' | 'mixed'>
  activities:   ConditionalActivity[]
}

export interface ErrorCorrection extends BaseQuestion {
  type:            'error_correction'
  originalText:    string
  errorTypes:      string[]
  correctedAnswer: string
}

export interface SentenceManipulation extends BaseQuestion {
  type:           'sentence_manipulation'
  subtype:        'combining' | 'splitting'
  inputSentences: string[]
  expectedOutput: string
  targetStructure: string
}

export type TextEntryQuestion =
  | Cloze
  | ShortAnswer
  | GrammarTransformation
  | ReportedSpeech
  | PassiveVoice
  | ConditionalBuilder
  | ErrorCorrection
  | SentenceManipulation
