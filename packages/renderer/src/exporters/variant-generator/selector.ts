import { deterministicShuffle } from './shuffler.js'
import type { QuestionBankEntry, VariantConfig } from './types.js'

// Per-topic coverage with proportional selection
// Each topic gets exactly config.topics[i].count questions
export function selectQuestions(
  bank: QuestionBankEntry[],
  config: VariantConfig,
  seed: number,
): QuestionBankEntry[] {
  const selected: QuestionBankEntry[] = []

  for (const topicConfig of config.topics) {
    const pool    = bank.filter(q => q.topic === topicConfig.name)
    // Use topic name length as seed salt to get different orderings per topic
    const shuffled = deterministicShuffle(pool, seed + topicConfig.name.length)
    selected.push(...shuffled.slice(0, topicConfig.count))
  }

  // Final shuffle of the whole selection
  return deterministicShuffle(selected, seed)
}
