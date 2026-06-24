import type { BaseQuestion } from '../base.js'

export interface MatchColumn {
  id:   string
  text: string
}

export interface MatchPair {
  left:  string
  right: string
}

export interface Matching extends BaseQuestion {
  type:          'matching'
  instructions:  string
  leftColumn:    MatchColumn[]
  rightColumn:   Array<MatchColumn & { isDistractor?: boolean }>
  correctMatches: MatchPair[]
}

export interface MatchingVocabulary extends BaseQuestion {
  type:       'matching_vocabulary'
  matchType:  'definition' | 'synonym' | 'antonym'
  leftColumn: MatchColumn[]
  rightColumn: Array<MatchColumn & { isDistractor?: boolean }>
}

export interface CollocationPair {
  left:  string
  right: string
}

export interface Collocation extends BaseQuestion {
  type:             'collocation'
  collocationType:  'verb_noun' | 'adjective_noun' | 'adverb_adjective' | 'verb_preposition'
  leftItems:        string[]
  rightItems:       string[]
  correctPairs:     CollocationPair[]
}

export interface IdiomEntry {
  idiom:   string
  meaning: string
}

export interface Idioms extends BaseQuestion {
  type:     'idioms'
  activity: {
    type:   'match_meaning' | 'fill_blank' | 'identify_context'
    idioms: IdiomEntry[]
  }
}

export interface Morpheme {
  part:    string
  type:    'prefix' | 'root' | 'suffix'
  meaning: string
}

export interface WordAnalysis extends BaseQuestion {
  type:      'word_analysis'
  word:      string
  morphemes: Morpheme[]
  questions: Array<{ stem: string; correctAnswer: string }>
}

export type MatchQuestion =
  | Matching
  | MatchingVocabulary
  | Collocation
  | Idioms
  | WordAnalysis
