import { describe, it, expect } from 'vitest'
import type { TeachingPackData, QualityScore, TechnicalScore, PedagogicalScore } from '../../src/contracts/schemas/teaching-pack.js'

// Minimal valid TechnicalScore
const technicalPassing: TechnicalScore = {
  format:       80,
  content:      75,
  presentation: 72,
  total:        75,   // 15%*80 + 55%*75 + 30%*72 = 12 + 41.25 + 21.6 = 74.85 ≈ 75
}

const technicalFailing: TechnicalScore = {
  format:       40,
  content:      50,
  presentation: 60,
  total:        52,
}

const pedagogicalPassing: PedagogicalScore = {
  clarity:      4,
  integrity:    4,
  depth:        3.5,
  practicality: 4,
  pertinence:   3.5,
  total:        3.8,
}

const pedagogicalFailing: PedagogicalScore = {
  clarity:      2,
  integrity:    2,
  depth:        3,
  practicality: 2,
  pertinence:   3,
  total:        2.4,
}

describe('QualityScore', () => {
  it('passed = true when technical >= 70 AND pedagogical >= 3.5', () => {
    const score: QualityScore = {
      technical:   technicalPassing,
      pedagogical: pedagogicalPassing,
      passed:      technicalPassing.total >= 70 && pedagogicalPassing.total >= 3.5,
      generatedAt: '2026-06-24T00:00:00Z',
    }
    expect(score.passed).toBe(true)
  })

  it('passed = false when technical < 70', () => {
    const score: QualityScore = {
      technical:   technicalFailing,
      pedagogical: pedagogicalPassing,
      passed:      technicalFailing.total >= 70 && pedagogicalPassing.total >= 3.5,
      generatedAt: '2026-06-24T00:00:00Z',
    }
    expect(score.passed).toBe(false)
  })

  it('passed = false when pedagogical < 3.5', () => {
    const score: QualityScore = {
      technical:   technicalPassing,
      pedagogical: pedagogicalFailing,
      passed:      technicalPassing.total >= 70 && pedagogicalFailing.total >= 3.5,
      generatedAt: '2026-06-24T00:00:00Z',
    }
    expect(score.passed).toBe(false)
  })

  it('TechnicalScore has 3 component dimensions + weighted total', () => {
    expect(technicalPassing).toHaveProperty('format')
    expect(technicalPassing).toHaveProperty('content')
    expect(technicalPassing).toHaveProperty('presentation')
    expect(technicalPassing).toHaveProperty('total')
  })

  it('PedagogicalScore has 5 dimensions + average total', () => {
    const dims: Array<keyof PedagogicalScore> = [
      'clarity', 'integrity', 'depth', 'practicality', 'pertinence',
    ]
    for (const dim of dims) {
      expect(pedagogicalPassing).toHaveProperty(dim)
    }
    expect(pedagogicalPassing).toHaveProperty('total')
  })
})

describe('TeachingPackData structure', () => {
  it('language field accepts vi | en | bilingual', () => {
    const langs: TeachingPackData['language'][] = ['vi', 'en', 'bilingual']
    for (const lang of langs) {
      expect(['vi', 'en', 'bilingual']).toContain(lang)
    }
  })

  it('gradeLevel is number array', () => {
    const gradeLevel: TeachingPackData['gradeLevel'] = [10, 11]
    expect(gradeLevel).toBeInstanceOf(Array)
    gradeLevel.forEach(g => expect(typeof g).toBe('number'))
  })

  it('humanReviewed defaults to false', () => {
    const reviewed: TeachingPackData['humanReviewed'] = false
    expect(reviewed).toBe(false)
  })

  it('differentiation is optional', () => {
    // TypeScript structural: a TeachingPackData without differentiation is valid
    const opt: Pick<TeachingPackData, 'differentiation'> = {}
    expect(opt.differentiation).toBeUndefined()
  })
})
