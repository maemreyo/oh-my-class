import { describe, expect, it } from 'vitest'
import type { Cloze } from '@oh-my-class/renderer/contracts/questions/types/text-entry.js'
import type { ClozeMixed, FillBlankWordBank } from '@oh-my-class/renderer/contracts/questions/types/fill-gap.js'
import { clozeBasicToH5PBlanks, clozeToH5PBlanks, fillBlankToH5PBlanks } from '../src/h5p-impl/content-types/blanks.js'

const baseMeta = {
  difficulty: 'remember' as const,
  tags: [],
  metadata: { subject: 'english' as const, grade: 8, topic: 'grammar' },
}

const clozeMixed: ClozeMixed = {
  ...baseMeta,
  id: 'cloze-mixed-001',
  type: 'cloze_mixed',
  clozeSubtype: 'grammar',
  passage: 'She ___ to school every day because she ___ learning.',
  blanks: [
    { id: 1, correctAnswer: 'goes', type: 'grammar' },
    { id: 2, correctAnswer: 'enjoys', type: 'vocabulary' },
  ],
}

const fillBlank: FillBlankWordBank = {
  ...baseMeta,
  id: 'fill-blank-001',
  type: 'fill_blank_wordbank',
  context: 'The cat sat on the ___.',
  blanks: [{ id: 1, correctAnswer: 'mat' }],
  wordBank: ['mat', 'hat', 'bat'],
  distractors: ['hat', 'bat'],
  shuffleWordBank: true,
}

const clozeBasic: Cloze = {
  ...baseMeta,
  id: 'cloze-basic-001',
  type: 'cloze',
  clozeType: 'vocabulary',
  passage: 'The ___ is blue.',
  blanks: [{ id: 1, correctAnswer: 'sky' }],
  caseSensitive: true,
}

describe('H5P blanks mappers', () => {
  it('maps cloze_mixed blanks into H5P answer markers sequentially', () => {
    const content = clozeToH5PBlanks(clozeMixed)

    expect(content.text).toBe('<p>She *goes* to school every day because she *enjoys* learning.</p>')
  })

  it('maps fill_blank_wordbank blanks into H5P answer markers', () => {
    const content = fillBlankToH5PBlanks(fillBlank)

    expect(content.text).toBe('<p>The cat sat on the *mat*.</p>')
  })

  it('maps basic cloze and preserves case sensitivity', () => {
    const content = clozeBasicToH5PBlanks(clozeBasic)

    expect(content.text).toBe('<p>The *sky* is blue.</p>')
    expect(content.behaviour.caseSensitive).toBe(true)
  })

  it('returns the H5P.Blanks behaviour and l10n shape', () => {
    const content = fillBlankToH5PBlanks(fillBlank)

    expect(content.behaviour).toEqual({
      enableRetry: true,
      enableSolutionsButton: true,
      caseSensitive: false,
    })
    expect(content.l10n).toEqual({ checkAnswer: 'Check', showSolution: 'Show solution', tryAgain: 'Retry' })
  })
})
