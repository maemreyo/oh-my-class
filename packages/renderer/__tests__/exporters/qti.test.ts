import { describe, it, expect } from 'vitest'
import { QTIExporter } from '../../src/exporters/qti/index.js'
import type { BaseQuestion } from '../../src/contracts/questions/base.js'
import type { MultipleChoiceSingle, TrueFalse4Item } from '../../src/contracts/questions/types/choice.js'

const baseMeta = {
  id:         'q1',
  difficulty: 'remember' as const,
  tags:       [],
  metadata:   { subject: 'english' as const, grade: 10, topic: 'grammar' },
}

const mcQuestion: MultipleChoiceSingle = {
  ...baseMeta,
  id:      'mc-001',
  type:    'multiple_choice_single',
  stem:    'What is the capital of France?',
  options: [
    { id: 'A', text: 'London',  isCorrect: false },
    { id: 'B', text: 'Paris',   isCorrect: true  },
    { id: 'C', text: 'Berlin',  isCorrect: false },
    { id: 'D', text: 'Madrid',  isCorrect: false },
  ],
}

const tf4Question: TrueFalse4Item = {
  ...baseMeta,
  id:    'tf-001',
  type:  'true_false_4item',
  stem:  'Mark T/F for each',
  items: [
    { id: 'a', text: 'Paris is in France', isTrue: true  },
    { id: 'b', text: 'London is in France', isTrue: false },
    { id: 'c', text: 'France is in Europe', isTrue: true  },
    { id: 'd', text: 'France borders Russia', isTrue: false },
  ],
}

const exporter = new QTIExporter()

describe('QTIExporter.export([])', () => {
  it('returns valid XML string for empty array', () => {
    const xml = exporter.export([])
    expect(typeof xml).toBe('string')
    expect(xml).toContain('<?xml version="1.0" encoding="UTF-8"?>')
    expect(xml).toContain('assessmentTest')
  })

  it('wraps items in assessmentTest > testPart > assessmentSection', () => {
    const xml = exporter.export([mcQuestion])
    expect(xml).toContain('assessmentTest')
    expect(xml).toContain('testPart')
    expect(xml).toContain('assessmentSection')
  })
})

describe('QTIExporter.exportOne()', () => {
  it('produces assessmentItem for MC question', () => {
    const xml = exporter.exportOne(mcQuestion)
    expect(xml).toContain('<?xml version="1.0" encoding="UTF-8"?>')
    expect(xml).toContain('assessmentItem')
    expect(xml).toContain('choiceInteraction')
    expect(xml).toContain('mc-001')
  })

  it('includes correct response declaration for MC', () => {
    const xml = exporter.exportOne(mcQuestion)
    expect(xml).toContain('responseDeclaration')
    expect(xml).toContain('correctResponse')
    expect(xml).toContain('<value>B</value>')
  })

  it('produces valid XML for TF 4-item', () => {
    const xml = exporter.exportOne(tf4Question)
    expect(xml).toContain('assessmentItem')
    expect(xml).toContain('tf-001')
    expect(xml).toContain('choiceInteraction')
  })

  it('escapes XML special characters in stem', () => {
    const q: MultipleChoiceSingle = {
      ...mcQuestion,
      id:   'esc-001',
      stem: 'What is 2 < 3 & 4 > 1?',
    }
    const xml = exporter.exportOne(q)
    expect(xml).toContain('&lt;')
    expect(xml).toContain('&gt;')
    expect(xml).toContain('&amp;')
    expect(xml).not.toContain('2 < 3')
  })

  it('throws for unknown question type', () => {
    const unknown: BaseQuestion = { ...baseMeta, type: 'unknown_type_xyz' }
    expect(() => exporter.exportOne(unknown)).toThrow()
  })

  it('IQTISerializer interface: all 8 families produce valid XML', () => {
    const testCases = [
      'multiple_choice_single',
      'cloze',
      'fill_blank_wordbank',
      'matching',
      'ordering',
      'essay',
      'drag_and_drop',
      'multimedia_video',
    ] as const
    for (const type of testCases) {
      const q = buildMinimalQuestion(type) as BaseQuestion
      const xml = exporter.exportOne(q)
      expect(xml).toContain('assessmentItem')
      expect(xml).toContain('<?xml')
    }
  })
})

function buildMinimalQuestion(type: string): Record<string, unknown> {
  const base = {
    id:         `test-${type}`,
    difficulty: 'remember',
    tags:       [],
    metadata:   { subject: 'all', grade: 5, topic: 'test' },
    type,
  }
  switch (type) {
    case 'multiple_choice_single':
      return { ...base, stem: 'stem', options: [
        { id: 'A', text: 'a', isCorrect: true },
        { id: 'B', text: 'b', isCorrect: false },
      ] }
    case 'cloze':
      return { ...base, clozeType: 'grammar', passage: 'Hello ___', blanks: [{ id: 1, correctAnswer: 'world' }], caseSensitive: false }
    case 'fill_blank_wordbank':
      return { ...base, context: 'Fill ___', blanks: [{ id: 1, correctAnswer: 'it' }], wordBank: ['it', 'on'], distractors: [], shuffleWordBank: true }
    case 'matching':
      return { ...base, instructions: 'Match', leftColumn: [{ id: 'L1', text: 'A' }], rightColumn: [{ id: 'R1', text: 'B' }], correctMatches: [{ left: 'L1', right: 'R1' }] }
    case 'ordering':
      return { ...base, instructions: 'Order these', items: [{ id: 1, text: 'First', correctPosition: 0 }, { id: 2, text: 'Second', correctPosition: 1 }] }
    case 'essay':
      return { ...base, prompt: 'Write an essay' }
    case 'drag_and_drop':
      return { ...base, instructions: 'Drag', zones: [{ id: 'Z1', label: 'Zone 1' }], draggables: [{ id: 'D1', text: 'Item', correctZone: 'Z1' }] }
    case 'multimedia_video':
      return { ...base, instructions: 'Record a video', maxDuration: 60 }
    default:
      return base
  }
}
