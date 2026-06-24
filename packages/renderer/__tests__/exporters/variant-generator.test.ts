import { describe, it, expect } from 'vitest'
import {
  deterministicShuffle,
  generateVariants,
  validateVariant,
  validateUniqueness,
} from '../../src/exporters/variant-generator/index.js'
import type { QuestionBankEntry, VariantConfig } from '../../src/exporters/variant-generator/types.js'

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeBank(count: number): QuestionBankEntry[] {
  return Array.from({ length: count }, (_, i) => ({
    id:         `q${i + 1}`,
    type:       'multiple_choice_single',
    difficulty: 'remember' as const,
    tags:       [],
    topic:      i < count / 2 ? 'algebra' : 'geometry',
    metadata:   { subject: 'math' as const, grade: 10, topic: i < count / 2 ? 'algebra' : 'geometry' },
  }))
}

const bank = makeBank(100)  // 50 algebra + 50 geometry

const config: VariantConfig = {
  totalQuestions: 10,
  topics: [
    { name: 'algebra',  count: 5 },
    { name: 'geometry', count: 5 },
  ],
  variantCount: 24,
  seed: 42,
}

// ── deterministicShuffle ──────────────────────────────────────────────────────

describe('deterministicShuffle', () => {
  it('is deterministic: same seed → same order', () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    const a = deterministicShuffle(items, 42)
    const b = deterministicShuffle(items, 42)
    expect(a).toEqual(b)
  })

  it('different seeds → different orders (almost always)', () => {
    const items = Array.from({ length: 20 }, (_, i) => i)
    const a = deterministicShuffle(items, 42)
    const b = deterministicShuffle(items, 43)
    expect(a).not.toEqual(b)
  })

  it('preserves all elements', () => {
    const items = ['a', 'b', 'c', 'd', 'e']
    const shuffled = deterministicShuffle(items, 42)
    expect(shuffled).toHaveLength(items.length)
    expect(shuffled.sort()).toEqual(items.sort())
  })

  it('does not mutate original array', () => {
    const items = [1, 2, 3, 4, 5]
    const original = [...items]
    deterministicShuffle(items, 42)
    expect(items).toEqual(original)
  })

  it('seed=42 produces deterministic result', () => {
    const first = deterministicShuffle([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 42)
    // Run again, same input and seed
    const second = deterministicShuffle([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 42)
    expect(first).toEqual(second)
  })
})

// ── generateVariants ──────────────────────────────────────────────────────────

describe('generateVariants', () => {
  it('generates the requested number of variants (24)', () => {
    const variants = generateVariants(bank, config)
    expect(variants).toHaveLength(24)
  })

  it('each variant has the correct total question count (10)', () => {
    const variants = generateVariants(bank, config)
    for (const v of variants) {
      expect(v.questions).toHaveLength(10)
    }
  })

  it('each variant has correct coverage (5 algebra, 5 geometry)', () => {
    const variants = generateVariants(bank, config)
    for (const v of variants) {
      expect(v.coverage['algebra']).toBe(5)
      expect(v.coverage['geometry']).toBe(5)
    }
  })

  it('all variants are unique (no two have the same question sequence)', () => {
    const variants = generateVariants(bank, config)
    const signatures = variants.map(v => v.questions.map(q => q.id).join(','))
    const unique = new Set(signatures)
    expect(unique.size).toBe(24)
  })

  it('variant IDs are V01..V24', () => {
    const variants = generateVariants(bank, config)
    expect(variants[0]!.variantId).toBe('V01')
    expect(variants[23]!.variantId).toBe('V24')
  })

  it('is deterministic: same config produces same variants', () => {
    const a = generateVariants(bank, config)
    const b = generateVariants(bank, config)
    expect(a.map(v => v.questions.map(q => q.id))).toEqual(
      b.map(v => v.questions.map(q => q.id))
    )
  })

  it('throws when bank is too small to generate unique variants', () => {
    // 1 question → every variant is identical → uniqueness check fires
    const tinyBank: QuestionBankEntry[] = [
      { id: 'q1', type: 'mc', difficulty: 'remember', tags: [], topic: 'algebra', metadata: { subject: 'math', grade: 10, topic: 'algebra' } },
    ]
    const smallConfig: VariantConfig = {
      totalQuestions: 1,
      topics: [{ name: 'algebra', count: 1 }],
      variantCount: 3,
      seed: 42,
    }
    expect(() => generateVariants(tinyBank, smallConfig)).toThrow('duplicate')
  })
})

// ── validateVariant ───────────────────────────────────────────────────────────

describe('validateVariant', () => {
  it('passes valid variant', () => {
    const variant = generateVariants(bank, config)[0]!
    const result  = validateVariant(variant, config)
    expect(result.valid).toBe(true)
    expect(result.errors).toHaveLength(0)
  })

  it('fails when question count is wrong', () => {
    const variant = generateVariants(bank, { ...config, totalQuestions: 5 })[0]!
    const wrongConfig = { ...config, totalQuestions: 20 }
    const result = validateVariant(variant, wrongConfig)
    expect(result.valid).toBe(false)
    expect(result.errors.some(e => e.includes('Expected 20'))).toBe(true)
  })
})

// ── validateUniqueness ────────────────────────────────────────────────────────

describe('validateUniqueness', () => {
  it('passes when all variants are unique', () => {
    const variants = generateVariants(bank, config)
    const result = validateUniqueness(variants)
    expect(result.valid).toBe(true)
  })

  it('fails when there are duplicates', () => {
    const variants = generateVariants(bank, { ...config, variantCount: 2 })
    const withDup = [...variants, variants[0]!]
    const result = validateUniqueness(withDup)
    expect(result.valid).toBe(false)
  })
})
