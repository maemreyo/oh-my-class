import { describe, expect, it } from 'vitest'
import { buildInverseThinkingGoogleFormsRequests, supportForInverseThinking } from '../src/inverse-thinking.js'
import { inverseThinkingPack } from './inverse-thinking-fixture.js'

describe('inverse-thinking Google Forms mapping', () => {
  it('builds requests and emits degradation warnings for feedback limitations', () => {
    const result = buildInverseThinkingGoogleFormsRequests(inverseThinkingPack)

    expect(supportForInverseThinking('google_forms').level).toBe('lossy')
    expect(result.warnings.join(' ')).toContain('Safe-zone feedback')
    expect(result.requests).toHaveLength(1)
    expect(result.requests[0].createItem.item.title).toContain('The Vanishing Time Marker')
    expect(result.requests[0].createItem.item.questionItem.question.grading?.correctAnswers?.answers[0].value).toContain('Use simple past')
  })
})
