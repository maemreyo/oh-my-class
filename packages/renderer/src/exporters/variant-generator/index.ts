import { selectQuestions } from './selector.js'
import { validateVariant, validateUniqueness } from './validator.js'
import type { QuestionBankEntry, VariantConfig, ExamVariant } from './types.js'

export type { QuestionBankEntry, VariantConfig, ExamVariant } from './types.js'
export { deterministicShuffle } from './shuffler.js'
export { selectQuestions } from './selector.js'
export { validateVariant, validateUniqueness } from './validator.js'

// EV1: deterministic seed-based exam variant generation
// Each variant uses seed + variantIndex so outputs are reproducible
export function generateVariants(
  bank:   QuestionBankEntry[],
  config: VariantConfig,
): ExamVariant[] {
  const variants: ExamVariant[] = []

  for (let i = 0; i < config.variantCount; i++) {
    const variantSeed = config.seed + i * 31607  // prime offset per variant
    const questions   = selectQuestions(bank, config, variantSeed)

    const coverage: Record<string, number> = {}
    for (const q of questions) {
      coverage[q.topic] = (coverage[q.topic] ?? 0) + 1
    }

    variants.push({
      variantId: `V${String(i + 1).padStart(2, '0')}`,
      seed:      variantSeed,
      questions,
      coverage,
    })
  }

  const uniquenessCheck = validateUniqueness(variants)
  if (!uniquenessCheck.valid) {
    throw new Error(`generateVariants: ${uniquenessCheck.errors.join('; ')}`)
  }

  return variants
}
