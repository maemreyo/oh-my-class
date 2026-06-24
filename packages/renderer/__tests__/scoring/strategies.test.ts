import { describe, it, expect } from 'vitest'
import { vietnameseTF2025, MOET_SCALE } from '../../src/scoring/strategies/vietnamese-tf-2025.js'
import { allOrNothing } from '../../src/scoring/strategies/all-or-nothing.js'
import { partialCredit } from '../../src/scoring/strategies/partial-credit.js'
import { rubricScoring } from '../../src/scoring/strategies/rubric.js'
import type { TrueFalse4Item } from '../../src/contracts/questions/types/choice.js'
import type { MultipleChoiceMultiple } from '../../src/contracts/questions/types/choice.js'
import type { RubricQuestion } from '../../src/scoring/strategies/rubric.js'

// ── Fixtures ─────────────────────────────────────────────────────────────────

const baseMeta = {
  id:         'q1',
  difficulty: 'remember' as const,
  tags:       [],
  metadata:   { subject: 'english' as const, grade: 10, topic: 'grammar' },
}

const tf4Question: TrueFalse4Item = {
  ...baseMeta,
  type:  'true_false_4item',
  stem:  'Mark T/F for each statement',
  items: [
    { id: 'a', text: 'Statement A', isTrue: true  },
    { id: 'b', text: 'Statement B', isTrue: false },
    { id: 'c', text: 'Statement C', isTrue: true  },
    { id: 'd', text: 'Statement D', isTrue: false },
  ],
}

// ── MOET_SCALE ────────────────────────────────────────────────────────────────

describe('MOET_SCALE', () => {
  it('has exact values [0, 0.1, 0.25, 0.5, 1.0]', () => {
    expect(MOET_SCALE[0]).toBe(0)
    expect(MOET_SCALE[1]).toBe(0.1)
    expect(MOET_SCALE[2]).toBe(0.25)
    expect(MOET_SCALE[3]).toBe(0.5)
    expect(MOET_SCALE[4]).toBe(1.0)
  })

  it('has exactly 5 values', () => {
    expect(MOET_SCALE.length).toBe(5)
  })
})

// ── vietnameseTF2025 ──────────────────────────────────────────────────────────

describe('vietnameseTF2025', () => {
  // tf4Question items: a=true, b=false, c=true, d=false
  it('0 correct → 0 points', () => {
    // All wrong: opposite of isTrue for each item
    const result = vietnameseTF2025.score(tf4Question, {
      answers: [false, true, false, true],
    })
    expect(result.points).toBe(0)
    expect(result.correctCount).toBe(0)
  })

  it('1 correct → 0.1 points', () => {
    // a correct (true=true), b wrong (true≠false), c wrong (false≠true), d wrong (true≠false)
    const result = vietnameseTF2025.score(tf4Question, {
      answers: [true, true, false, true],
    })
    expect(result.points).toBe(0.1)
    expect(result.correctCount).toBe(1)
  })

  it('2 correct → 0.25 points', () => {
    // a correct (true), b correct (false), c wrong (false≠true), d wrong (true≠false)
    const result = vietnameseTF2025.score(tf4Question, {
      answers: [true, false, false, true],
    })
    expect(result.points).toBe(0.25)
    expect(result.correctCount).toBe(2)
  })

  it('3 correct → 0.5 points', () => {
    // a correct, b correct, c correct, d wrong
    const result = vietnameseTF2025.score(tf4Question, {
      answers: [true, false, true, true],
    })
    expect(result.points).toBe(0.5)
    expect(result.correctCount).toBe(3)
  })

  it('4 correct → 1.0 points', () => {
    // All correct: a=true, b=false, c=true, d=false
    const result = vietnameseTF2025.score(tf4Question, {
      answers: [true, false, true, false],
    })
    expect(result.points).toBe(1.0)
    expect(result.correctCount).toBe(4)
    expect(result.maxPoints).toBe(1.0)
  })

  it('produces breakdown with correct itemIds', () => {
    const result = vietnameseTF2025.score(tf4Question, {
      answers: [true, false, true, false],
    })
    expect(result.breakdown).toHaveLength(4)
    expect(result.breakdown![0]!.itemId).toBe('a')
    expect(result.breakdown![0]!.correct).toBe(true)
    expect(result.breakdown![1]!.itemId).toBe('b')
    expect(result.breakdown![1]!.correct).toBe(true)
  })
})

// ── allOrNothing ──────────────────────────────────────────────────────────────

describe('allOrNothing', () => {
  const q: Parameters<typeof allOrNothing.score>[0] = {
    ...baseMeta,
    type:    'short_answer',
    scoring: { type: 'all_or_nothing' as const, pointsTotal: 2 },
  }

  it('correct → full points', () => {
    const result = allOrNothing.score(q, { answer: 'Paris' })
    expect(result.points).toBe(2)
    expect(result.maxPoints).toBe(2)
  })

  it('empty answer → 0 points', () => {
    const result = allOrNothing.score(q, { answer: '' })
    expect(result.points).toBe(0)
  })
})

// ── partialCredit ─────────────────────────────────────────────────────────────

describe('partialCredit', () => {
  const mcMultiple: MultipleChoiceMultiple = {
    ...baseMeta,
    type:    'multiple_choice_multiple',
    stem:    'Select all correct',
    options: [
      { id: 'A', text: 'Option A', isCorrect: true  },
      { id: 'B', text: 'Option B', isCorrect: true  },
      { id: 'C', text: 'Option C', isCorrect: false },
      { id: 'D', text: 'Option D', isCorrect: false },
    ],
    scoring: { type: 'partial_credit', pointsTotal: 1 },
  }

  it('all correct → 1.0 points', () => {
    const r = partialCredit.score(mcMultiple, { selectedIds: ['A', 'B'] })
    expect(r.points).toBe(1.0)
    expect(r.correctCount).toBe(2)
  })

  it('half correct, no wrong → 0.5 points', () => {
    const r = partialCredit.score(mcMultiple, { selectedIds: ['A'] })
    expect(r.points).toBe(0.5)
  })

  it('wrong selection → penalty applied', () => {
    const withPenalty: MultipleChoiceMultiple = {
      ...mcMultiple,
      scoring: { type: 'partial_credit', pointsTotal: 1, penaltyPerWrong: 0.25 },
    }
    const r = partialCredit.score(withPenalty, { selectedIds: ['A', 'C'] })
    // 0.5 correct - 0.25 wrong = 0.25
    expect(r.points).toBe(0.25)
  })

  it('points never go below 0', () => {
    const withPenalty: MultipleChoiceMultiple = {
      ...mcMultiple,
      scoring: { type: 'partial_credit', pointsTotal: 1, penaltyPerWrong: 1 },
    }
    const r = partialCredit.score(withPenalty, { selectedIds: ['C', 'D'] })
    expect(r.points).toBeGreaterThanOrEqual(0)
  })
})

// ── rubricScoring ─────────────────────────────────────────────────────────────

describe('rubricScoring', () => {
  const rubricQ: RubricQuestion = {
    ...baseMeta,
    type:    'essay',
    scoring: { type: 'rubric', pointsTotal: 10 },
    rubric:  {
      criteria: [
        {
          name:   'Content',
          weight: 60,
          levels: [{ score: 0, description: 'poor' }, { score: 1, description: 'excellent' }],
        },
        {
          name:   'Grammar',
          weight: 40,
          levels: [{ score: 0, description: 'poor' }, { score: 1, description: 'excellent' }],
        },
      ],
    },
  }

  it('full marks on all criteria → maxPoints', () => {
    const r = rubricScoring.score(rubricQ, {
      criterionScores: { Content: 1, Grammar: 1 },
    })
    expect(r.points).toBeCloseTo(10)
    expect(r.maxPoints).toBe(10)
  })

  it('zero on all criteria → 0 points', () => {
    const r = rubricScoring.score(rubricQ, {
      criterionScores: { Content: 0, Grammar: 0 },
    })
    expect(r.points).toBe(0)
  })

  it('partial scores → proportional result', () => {
    const r = rubricScoring.score(rubricQ, {
      criterionScores: { Content: 1, Grammar: 0 },
    })
    // Content (weight 60/100) fully scored, Grammar (weight 40/100) zero
    expect(r.points).toBeCloseTo(6)
  })
})
