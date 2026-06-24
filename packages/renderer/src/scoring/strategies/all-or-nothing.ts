import type { ScoringStrategy, ScoreResult } from '../types.js'
import type { BaseQuestion } from '../../contracts/questions/base.js'

export interface AllOrNothingResponse {
  answer: string | string[] | boolean
}

// Binary: full points if correct, zero otherwise
export const allOrNothing: ScoringStrategy<BaseQuestion, AllOrNothingResponse> = {
  score(question, response): ScoreResult {
    const maxPoints = question.scoring?.pointsTotal ?? 1.0
    const correct = checkCorrect(response.answer)
    return {
      points:    correct ? maxPoints : 0,
      maxPoints,
      feedback:  correct ? 'Correct' : 'Incorrect',
    }
  },
}

function checkCorrect(answer: string | string[] | boolean): boolean {
  if (typeof answer === 'boolean') return answer
  if (Array.isArray(answer)) return answer.length > 0
  return answer.trim().length > 0
}
