import { describe, expect, it } from 'vitest'
import { UnsupportedInverseThinkingExportError, exportInverseThinkingH5P, supportForInverseThinking } from '../src/inverse-thinking.js'
import { inverseThinkingPack } from './inverse-thinking-fixture.js'

describe('inverse-thinking H5P export', () => {
  it('fails with a typed unsupported-format error and remediation', async () => {
    expect(supportForInverseThinking('h5p').level).toBe('unsupported')
    await expect(exportInverseThinkingH5P(inverseThinkingPack)).rejects.toThrow(UnsupportedInverseThinkingExportError)
    await expect(exportInverseThinkingH5P(inverseThinkingPack)).rejects.toThrow('Use HTML, GIFT, or QTI')
  })
})
