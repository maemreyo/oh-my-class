import { describe, it, expect } from 'vitest'
import { GoogleFormsExporter, questionToFormsItem } from '../../src/exporters/google-forms/index.js'
import type { MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item } from '../../src/contracts/questions/types/choice.js'
import type { ShortAnswer } from '../../src/contracts/questions/types/text-entry.js'
import type { Essay } from '../../src/contracts/questions/types/open.js'

const baseMeta = {
  difficulty: 'remember' as const,
  tags: [],
  metadata: { subject: 'english' as const, grade: 9, topic: 'grammar' },
}

const mcSingle: MultipleChoiceSingle = {
  ...baseMeta,
  id:   'mc-gf-001',
  type: 'multiple_choice_single',
  stem: 'Which planet is largest?',
  options: [
    { id: 'A', text: 'Earth',  isCorrect: false },
    { id: 'B', text: 'Jupiter', isCorrect: true  },
    { id: 'C', text: 'Mars',   isCorrect: false  },
  ],
}

const mcMultiple: MultipleChoiceMultiple = {
  ...baseMeta,
  id:   'mc-gf-002',
  type: 'multiple_choice_multiple',
  stem: 'Select all mammals',
  options: [
    { id: 'A', text: 'Dolphin', isCorrect: true  },
    { id: 'B', text: 'Shark',   isCorrect: false },
    { id: 'C', text: 'Whale',   isCorrect: true  },
  ],
}

const tf4: TrueFalse4Item = {
  ...baseMeta,
  id:   'tf-gf-001',
  type: 'true_false_4item',
  stem: 'T/F questions',
  items: [
    { id: 'a', text: 'Water is H2O',       isTrue: true  },
    { id: 'b', text: 'Gold is a gas',      isTrue: false },
    { id: 'c', text: 'Iron is a metal',    isTrue: true  },
    { id: 'd', text: 'Oxygen is a liquid', isTrue: false },
  ],
}

const shortAnswer: ShortAnswer = {
  ...baseMeta,
  id:             'sa-gf-001',
  type:           'short_answer',
  stem:           'What is H2O?',
  correctAnswer:  'Water',
  acceptableAnswers: ['water'],
}

const essay: Essay = {
  ...baseMeta,
  id:     'es-gf-001',
  type:   'essay',
  prompt: 'Describe the water cycle.',
}

describe('questionToFormsItem', () => {
  it('maps multiple_choice_single to RADIO choiceQuestion', () => {
    const item = questionToFormsItem(mcSingle, 1)!
    expect(item).not.toBeNull()
    expect(item.title).toBe('Which planet is largest?')
    const cq = item.questionItem.question.choiceQuestion!
    expect(cq.type).toBe('RADIO')
    expect(cq.options).toHaveLength(3)
    expect(item.questionItem.question.grading?.correctAnswers?.answers[0].value).toBe('Jupiter')
  })

  it('maps multiple_choice_multiple to CHECKBOX choiceQuestion', () => {
    const item = questionToFormsItem(mcMultiple, 2)!
    expect(item.questionItem.question.choiceQuestion?.type).toBe('CHECKBOX')
    const answers = item.questionItem.question.grading?.correctAnswers?.answers ?? []
    expect(answers.map(a => a.value)).toContain('Dolphin')
    expect(answers.map(a => a.value)).toContain('Whale')
  })

  it('maps true_false_4item to CHECKBOX with TRUE items as correct', () => {
    const item = questionToFormsItem(tf4, 1)!
    const answers = item.questionItem.question.grading?.correctAnswers?.answers ?? []
    const trueTexts = answers.map(a => a.value)
    expect(trueTexts).toContain('Water is H2O')
    expect(trueTexts).toContain('Iron is a metal')
    expect(trueTexts).not.toContain('Gold is a gas')
  })

  it('maps short_answer to textQuestion (not paragraph)', () => {
    const item = questionToFormsItem(shortAnswer, 1)!
    expect(item.questionItem.question.textQuestion?.paragraph).toBe(false)
    const answers = item.questionItem.question.grading?.correctAnswers?.answers ?? []
    expect(answers.map(a => a.value)).toContain('Water')
    expect(answers.map(a => a.value)).toContain('water')
  })

  it('maps essay to textQuestion (paragraph)', () => {
    const item = questionToFormsItem(essay)!
    expect(item.questionItem.question.textQuestion?.paragraph).toBe(true)
  })

  it('returns null for unsupported question types', () => {
    const unknown = { ...baseMeta, id: 'x', type: 'matching' } as any
    expect(questionToFormsItem(unknown)).toBeNull()
  })
})

describe('GoogleFormsExporter.buildBatchUpdateRequests', () => {
  const gfExporter = new GoogleFormsExporter('fake-token')

  it('builds one request per supported question', () => {
    const reqs = gfExporter.buildBatchUpdateRequests([mcSingle, mcMultiple, essay])
    expect(reqs).toHaveLength(3)
    reqs.forEach((r, i) => {
      expect(r.createItem.location.index).toBe(i)
    })
  })

  it('skips unsupported question types', () => {
    const unknown = { ...baseMeta, id: 'x', type: 'cloze' } as any
    const reqs = gfExporter.buildBatchUpdateRequests([mcSingle, unknown])
    expect(reqs).toHaveLength(1)
  })

  it('sets pointValue from argument', () => {
    const reqs = gfExporter.buildBatchUpdateRequests([mcSingle], 5)
    expect(reqs[0].createItem.item.questionItem.question.grading?.pointValue).toBe(5)
  })
})
