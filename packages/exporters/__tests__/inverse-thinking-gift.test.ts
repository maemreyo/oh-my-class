import { describe, expect, it } from 'vitest'
import { exportInverseThinkingGift, supportForInverseThinking } from '../src/inverse-thinking.js'
import { inverseThinkingPack } from './inverse-thinking-fixture.js'

describe('inverse-thinking GIFT export', () => {
  it('preserves case title, disaster prompt, correct answer, and teacher rationale metadata', () => {
    const gift = exportInverseThinkingGift(inverseThinkingPack)

    expect(supportForInverseThinking('gift').level).toBe('supported')
    expect(gift).toContain('$CATEGORY: oh-my-class/inverse-thinking')
    expect(gift).toContain('::case-present-perfect::')
    expect(gift).toContain('The Vanishing Time Marker')
    expect(gift).toContain('I have visited Da Nang yesterday')
    expect(gift).toContain('=Use simple past with finished time')
    expect(gift).toContain('// teacher_rationale: The adverb yesterday conflicts with present perfect usage.')
  })
})
