import { describe, it, expect } from 'vitest'
import { GIFTExporter } from '../../src/exporters/gift/index.js'
import type { MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item } from '../../src/contracts/questions/types/choice.js'
import type { ShortAnswer, Cloze } from '../../src/contracts/questions/types/text-entry.js'
import type { Matching } from '../../src/contracts/questions/types/match.js'
import type { Essay } from '../../src/contracts/questions/types/open.js'
import type { QuizData } from '../../src/contracts/quiz.js'

const baseMeta = {
  difficulty: 'remember' as const,
  tags: [],
  metadata: { subject: 'english' as const, grade: 10, topic: 'test' },
}

const mcSingle: MultipleChoiceSingle = {
  ...baseMeta,
  id:   'mc-001',
  type: 'multiple_choice_single',
  stem: 'What is 2+2?',
  options: [
    { id: 'A', text: 'Three',  isCorrect: false },
    { id: 'B', text: 'Four',   isCorrect: true  },
    { id: 'C', text: 'Five',   isCorrect: false },
    { id: 'D', text: 'Six',    isCorrect: false },
  ],
}

const mcMultiple: MultipleChoiceMultiple = {
  ...baseMeta,
  id:   'mc-002',
  type: 'multiple_choice_multiple',
  stem: 'Which are prime numbers?',
  options: [
    { id: 'A', text: '2',  isCorrect: true  },
    { id: 'B', text: '4',  isCorrect: false },
    { id: 'C', text: '3',  isCorrect: true  },
    { id: 'D', text: '6',  isCorrect: false },
  ],
}

const tf4: TrueFalse4Item = {
  ...baseMeta,
  id:   'tf-001',
  type: 'true_false_4item',
  stem: 'Mark T/F',
  items: [
    { id: 'a', text: 'The sun is a star', isTrue: true  },
    { id: 'b', text: 'The moon is a star', isTrue: false },
    { id: 'c', text: 'Earth orbits the sun', isTrue: true  },
    { id: 'd', text: 'Mars is Earth', isTrue: false },
  ],
}

const shortAnswer: ShortAnswer = {
  ...baseMeta,
  id:             'sa-001',
  type:           'short_answer',
  stem:           'Name the capital of Vietnam.',
  correctAnswer:  'Hanoi',
  acceptableAnswers: ['Ha Noi'],
}

const cloze: Cloze = {
  ...baseMeta,
  id:      'cz-001',
  type:    'cloze',
  passage: 'The cat sat on the ___.',
  blanks:  [{ id: 'b1', position: 4, correctAnswer: 'mat', acceptableAnswers: [] }],
}

const matching: Matching = {
  ...baseMeta,
  id:           'mt-001',
  type:         'matching',
  instructions: 'Match the capital to its country.',
  leftColumn:   [{ id: 'L1', text: 'France' }, { id: 'L2', text: 'Vietnam' }],
  rightColumn:  [{ id: 'R1', text: 'Paris' }, { id: 'R2', text: 'Hanoi' }],
  correctMatches: [
    { left: 'L1', right: 'R1' },
    { left: 'L2', right: 'R2' },
  ],
}

const essay: Essay = {
  ...baseMeta,
  id:     'es-001',
  type:   'essay',
  prompt: 'Write a short essay about photosynthesis.',
}

const exporter = new GIFTExporter()

describe('GIFTExporter', () => {
  it('serialises multiple_choice_single with = for correct and ~ for wrong', () => {
    const out = exporter.export([mcSingle])
    expect(out).toContain('::mc-001::')
    expect(out).toContain('=Four')
    expect(out).toContain('~Three')
    expect(out).toContain('~Five')
  })

  it('serialises multiple_choice_multiple with percentage weights', () => {
    const out = exporter.export([mcMultiple])
    expect(out).toContain('::mc-002::')
    expect(out).toContain('%50%2')   // 2 correct → 100/2 = 50%
    expect(out).toContain('%50%3')
    expect(out).toContain('~4')
  })

  it('serialises true_false_4item as individual T/F items', () => {
    const out = exporter.export([tf4])
    expect(out).toContain('::tf-001-a::')
    expect(out).toContain('{ TRUE }')
    expect(out).toContain('::tf-001-b::')
    expect(out).toContain('{ FALSE }')
  })

  it('serialises short_answer with = for each accepted answer', () => {
    const out = exporter.export([shortAnswer])
    expect(out).toContain('::sa-001::')
    expect(out).toContain('=Hanoi')
    expect(out).toContain('=Ha Noi')
  })

  it('serialises cloze with passage and blank answers', () => {
    const out = exporter.export([cloze])
    expect(out).toContain('::cz-001::')
    expect(out).toContain('=mat')
  })

  it('serialises matching pairs with -> notation', () => {
    const out = exporter.export([matching])
    expect(out).toContain('=France->Paris')
    expect(out).toContain('=Vietnam->Hanoi')
  })

  it('serialises essay with empty braces', () => {
    const out = exporter.export([essay])
    expect(out).toContain('::es-001::')
    expect(out).toContain('{ }')
  })

  it('adds $CATEGORY header when category is provided', () => {
    const out = exporter.export([mcSingle], 'TestCat')
    expect(out).toMatch(/^\$CATEGORY: TestCat/)
  })

  it('skips unsupported question types silently', () => {
    const unknown = { ...baseMeta, id: 'x', type: 'unknown_type' } as any
    const out = exporter.export([unknown])
    expect(out.trim()).toBe('')
  })

  it('exportQuiz serialises MCQuestion options', () => {
    const quiz: QuizData = {
      title: 'My Quiz',
      subject: 'english',
      gradeLevel: '10',
      questions: [
        {
          id: 'q1-1',
          prompt: 'Capital of France?',
          options: [
            { label: 'A', text: 'London' },
            { label: 'B', text: 'Paris' },
          ],
          answer: 'B',
        },
      ],
    }
    const out = exporter.exportQuiz(quiz)
    expect(out).toContain('$CATEGORY: My_Quiz')
    expect(out).toContain('=Paris')
    expect(out).toContain('~London')
  })

  it('escapes GIFT special characters in stems', () => {
    const q: MultipleChoiceSingle = {
      ...baseMeta,
      id:   'esc-001',
      type: 'multiple_choice_single',
      stem: 'A {test} = 100# ~something',
      options: [
        { id: 'A', text: 'yes', isCorrect: true },
        { id: 'B', text: 'no',  isCorrect: false },
      ],
    }
    const out = exporter.export([q])
    expect(out).toContain('\\{test\\}')
    expect(out).toContain('\\=')
    expect(out).toContain('\\#')
  })
})
