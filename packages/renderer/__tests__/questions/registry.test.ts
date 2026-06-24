import { describe, it, expect } from 'vitest'
import {
  questionRegistry,
  QuestionTypeRegistry,
  FAMILY_MAP,
  RENDERING_FAMILIES,
} from '../../src/contracts/questions/index.js'

describe('FAMILY_MAP', () => {
  it('maps every registered type to exactly one RenderingFamily', () => {
    for (const [type, family] of Object.entries(FAMILY_MAP)) {
      expect(RENDERING_FAMILIES).toContain(family)
      expect(typeof type).toBe('string')
    }
  })

  it('covers all 8 rendering families', () => {
    const families = new Set(Object.values(FAMILY_MAP))
    for (const f of RENDERING_FAMILIES) {
      expect(families).toContain(f)
    }
  })
})

describe('questionRegistry singleton', () => {
  it('is auto-populated at module init (no manual registration needed)', () => {
    expect(questionRegistry.size()).toBeGreaterThan(0)
  })

  it('registers 40+ question types', () => {
    expect(questionRegistry.size()).toBeGreaterThanOrEqual(40)
  })

  it('every registered type exists in FAMILY_MAP', () => {
    for (const meta of questionRegistry.all()) {
      expect(FAMILY_MAP).toHaveProperty(meta.type)
      expect(FAMILY_MAP[meta.type]).toBe(meta.family)
    }
  })
})

describe('QuestionTypeRegistry.query()', () => {
  it('returns all types when no criteria given', () => {
    const all = questionRegistry.query({})
    expect(all.length).toBeGreaterThanOrEqual(40)
  })

  it('filters by artifactType', () => {
    const quizTypes = questionRegistry.query({ artifactType: 'quiz' })
    expect(quizTypes.length).toBeGreaterThan(0)
    for (const t of quizTypes) {
      expect(t.artifacts).toContain('quiz')
    }
  })

  it('filters by subject (respects "all" catch-all)', () => {
    const english = questionRegistry.query({ subject: 'english' })
    expect(english.length).toBeGreaterThan(0)
    for (const t of english) {
      expect(t.subjects.includes('english') || t.subjects.includes('all')).toBe(true)
    }
  })

  it('filters by requiresMedia=false excludes multimedia types', () => {
    const nonMedia = questionRegistry.query({ requiresMedia: false })
    const mediaTypes = nonMedia.filter(t => t.requiresMedia)
    expect(mediaTypes).toHaveLength(0)
  })

  it('filters by maxComplexity=low returns only low complexity', () => {
    const low = questionRegistry.query({ maxComplexity: 'low' })
    for (const t of low) {
      expect(t.complexity).toBe('low')
    }
  })

  it('filters by moetLevel returns only matching types', () => {
    const vanDungCao = questionRegistry.query({ moetLevel: 'van_dung_cao' })
    for (const t of vanDungCao) {
      expect(t.moetLevels).toContain('van_dung_cao')
    }
  })

  it('combined criteria: quiz + english + non-media + medium complexity', () => {
    const result = questionRegistry.query({
      artifactType:  'quiz',
      subject:       'english',
      requiresMedia: false,
      maxComplexity: 'medium',
    })
    expect(result.length).toBeGreaterThan(0)
    for (const t of result) {
      expect(t.artifacts).toContain('quiz')
      expect(t.requiresMedia).toBe(false)
      expect(['low', 'medium']).toContain(t.complexity)
    }
  })
})

describe('QuestionTypeRegistry.getFamily()', () => {
  it('returns correct family for known types', () => {
    expect(questionRegistry.getFamily('multiple_choice_single')).toBe('choice')
    expect(questionRegistry.getFamily('true_false_4item')).toBe('choice')
    expect(questionRegistry.getFamily('essay')).toBe('open')
    expect(questionRegistry.getFamily('drag_and_drop')).toBe('interactive')
    expect(questionRegistry.getFamily('multimedia_video')).toBe('multimedia')
    expect(questionRegistry.getFamily('fill_blank_wordbank')).toBe('fill-gap')
    expect(questionRegistry.getFamily('matching')).toBe('match')
    expect(questionRegistry.getFamily('ordering')).toBe('order')
  })

  it('throws for unknown type', () => {
    expect(() => questionRegistry.getFamily('unknown_type')).toThrow()
  })
})

describe('QuestionTypeRegistry.supports()', () => {
  it('returns true for supported artifact type', () => {
    expect(questionRegistry.supports('multiple_choice_single', 'quiz')).toBe(true)
  })

  it('returns false for unsupported artifact type', () => {
    expect(questionRegistry.supports('multiple_choice_single', 'infographic')).toBe(false)
  })

  it('returns false for unknown type', () => {
    expect(questionRegistry.supports('unknown_xyz', 'quiz')).toBe(false)
  })
})

describe('QuestionTypeRegistry.register() validation', () => {
  it('throws when registering a type not in FAMILY_MAP', () => {
    const reg = new QuestionTypeRegistry()
    expect(() => reg.register({
      type:           'not_in_family_map',
      family:         'choice',
      label:          'Test',
      labelVi:        'Test',
      artifacts:      ['quiz'],
      bloomLevels:    ['remember'],
      subjects:       ['all'],
      examFormats:    ['general'],
      requiresMedia:  false,
      isInteractive:  false,
      complexity:     'low',
      qtiInteraction: 'choiceInteraction',
    })).toThrow('FAMILY_MAP')
  })
})
