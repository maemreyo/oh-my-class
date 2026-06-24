import type { BaseQuestion } from '../questions/base.js'

export interface MediaAttachment {
  src:     string   // data URI only
  alt:     string
  kind:    'image' | 'audio' | 'video' | 'pdf'
  width?:  number
  height?: number
}

// WB1: 11 discriminated union variants
export type WorksheetBlock =
  | { type: 'text';           content: string }
  | { type: 'question';       question: BaseQuestion }
  | { type: 'table';          headers: string[]; rows: string[][] }
  | { type: 'blank_lines';    count: number; label?: string }
  | { type: 'space_for_work'; height: number }              // px — print scratch area
  | { type: 'fill_in_table';  headers: string[]; rows: (string | null)[][] }
  | { type: 'matching_lines'; pairs: Array<{ left: string; right: string; blank: boolean }> }
  | { type: 'diagram_space';  instructions: string }        // "Draw your answer here"
  | { type: 'code_block';     language: string; code: string }
  | { type: 'media';          attachment: MediaAttachment }
  | { type: 'svg';            svgContent: string }          // sanitized inline SVG

export interface WorksheetSection {
  id:           string
  type:         'instruction' | 'example' | 'practice' | 'challenge' | 'review'
  title:        string
  instruction?: string
  blocks:       WorksheetBlock[]
}

export interface Worksheet {
  id:           string
  title:        string
  instructions: string
  language:     'vi' | 'en' | 'bilingual'
  sections:     WorksheetSection[]
  metadata: {
    difficulty:        number      // 1-5
    estimatedTime:     number      // minutes
    answerKeyIncluded: boolean
    skillsPracticed:   string[]
    printOptimized:    boolean     // triggers print-specific CSS
  }
}
