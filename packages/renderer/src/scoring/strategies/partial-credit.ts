import type { ScoringStrategy, ScoreResult } from '../types.js'
import type { MultipleChoiceMultiple } from '../../contracts/questions/types/choice.js'

export interface PartialCreditResponse {
  selectedIds: string[]
}

// Proportional: points = (correct_selected / total_correct) * maxPoints
// Penalty applied for each incorrect selection if penaltyPerWrong is set
export const partialCredit: ScoringStrategy<MultipleChoiceMultiple, PartialCreditResponse> = {
  score(question, response): ScoreResult {
    const maxPoints = question.scoring?.pointsTotal ?? 1.0
    const penalty   = question.scoring?.penaltyPerWrong ?? 0

    const correctIds = question.options
      .filter(o => o.isCorrect)
      .map(o => o.id)

    const correctSelected = response.selectedIds.filter(id => correctIds.includes(id))
    const wrongSelected   = response.selectedIds.filter(id => !correctIds.includes(id))

    const raw = (correctSelected.length / correctIds.length) * maxPoints
           - wrongSelected.length * penalty

    return {
      points:       Math.max(0, raw),
      maxPoints,
      correctCount: correctSelected.length,
      totalItems:   correctIds.length,
      breakdown:    question.options.map(o => ({
        itemId:  o.id,
        correct: correctIds.includes(o.id)
          ? response.selectedIds.includes(o.id)
          : !response.selectedIds.includes(o.id),
      })),
    }
  },
}
