import type { ScoringStrategy, ScoreResult } from '../types.js'
import type { TrueFalse4Item } from '../../contracts/questions/types/choice.js'

export interface TFResponse {
  answers: [boolean, boolean, boolean, boolean]
}

// MOET Decision 764/QĐ-BGDĐT — non-linear partial credit
// 1 correct → 0.1đ, 2 → 0.25đ, 3 → 0.5đ, 4 → 1.0đ
const MOET_SCALE: readonly [number, number, number, number, number] = [
  0, 0.1, 0.25, 0.5, 1.0,
]

export { MOET_SCALE }

export const vietnameseTF2025: ScoringStrategy<TrueFalse4Item, TFResponse> = {
  score(question, response): ScoreResult {
    const correctCount = question.items.reduce(
      (acc, item, i) => acc + (item.isTrue === response.answers[i] ? 1 : 0),
      0,
    )

    return {
      points:       MOET_SCALE[correctCount],
      maxPoints:    1.0,
      correctCount,
      totalItems:   question.items.length,
      breakdown:    question.items.map((item, i) => ({
        itemId:  item.id,
        correct: item.isTrue === response.answers[i],
      })),
    }
  },
}
