import type { ExamVariant, VariantConfig } from './types.js'

export interface ValidationResult {
  valid:    boolean
  errors:   string[]
}

// Checks topic coverage and total question count
export function validateVariant(
  variant: ExamVariant,
  config:  VariantConfig,
): ValidationResult {
  const errors: string[] = []

  if (variant.questions.length !== config.totalQuestions) {
    errors.push(
      `Expected ${config.totalQuestions} questions, got ${variant.questions.length}`
    )
  }

  for (const topicConfig of config.topics) {
    const count = variant.questions.filter(q => q.topic === topicConfig.name).length
    if (count < topicConfig.count) {
      errors.push(
        `Topic "${topicConfig.name}": expected ${topicConfig.count}, got ${count}`
      )
    }
  }

  return { valid: errors.length === 0, errors }
}

// Checks that no two variants share the exact same question sequence
export function validateUniqueness(variants: ExamVariant[]): ValidationResult {
  const errors: string[] = []
  const seen = new Set<string>()

  for (const variant of variants) {
    const key = variant.questions.map(q => q.id).join(',')
    if (seen.has(key)) {
      errors.push(`Variant ${variant.variantId} is a duplicate`)
    }
    seen.add(key)
  }

  return { valid: errors.length === 0, errors }
}
