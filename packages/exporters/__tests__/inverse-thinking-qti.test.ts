import { describe, expect, it } from 'vitest'
import { exportInverseThinkingQTI, supportForInverseThinking } from '../src/inverse-thinking.js'
import { inverseThinkingPack } from './inverse-thinking-fixture.js'

describe('inverse-thinking QTI export', () => {
  it('emits QTI 2.1 XML with feedback blocks and case IDs', () => {
    const qti = exportInverseThinkingQTI(inverseThinkingPack)

    expect(supportForInverseThinking('qti').level).toBe('supported')
    expect(qti).toContain('imsqti_v2p1')
    expect(qti).toContain('identifier="case-present-perfect"')
    expect(qti).toContain('<correctResponse><value>A</value></correctResponse>')
    expect(qti).toContain('<modalFeedback')
    expect(qti).toContain('The adverb yesterday conflicts with present perfect usage.')
  })
})
