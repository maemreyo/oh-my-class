import type { ScoringStrategy, ScoreResult } from '../types.js'
import type { BaseQuestion, Rubric } from '../../contracts/questions/base.js'

export interface RubricResponse {
  criterionScores: Record<string, number>
  comments?:       Record<string, string>
}

export interface RubricQuestion extends BaseQuestion {
  rubric: Rubric
}

// Weighted rubric: sum(criterion_score * weight) / sum(weights) * maxPoints
export const rubricScoring: ScoringStrategy<RubricQuestion, RubricResponse> = {
  score(question, response): ScoreResult {
    const maxPoints = question.scoring?.pointsTotal ?? 1.0
    const { criteria } = question.rubric

    const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0)
    if (totalWeight === 0) {
      return { points: 0, maxPoints, feedback: 'Rubric has no criteria with weight' }
    }

    const weightedScore = criteria.reduce((sum, criterion) => {
      const raw   = response.criterionScores[criterion.name] ?? 0
      const max   = maxLevelScore(criterion)
      const ratio = max > 0 ? raw / max : 0
      return sum + ratio * criterion.weight
    }, 0)

    const points = (weightedScore / totalWeight) * maxPoints

    return {
      points:   Math.min(maxPoints, Math.max(0, points)),
      maxPoints,
      breakdown: criteria.map(c => ({
        itemId:  c.name,
        correct: (response.criterionScores[c.name] ?? 0) >= maxLevelScore(c),
      })),
    }
  },
}

function maxLevelScore(criterion: Rubric['criteria'][number]): number {
  if (criterion.levels && criterion.levels.length > 0) {
    return Math.max(...criterion.levels.map(l => l.score))
  }
  return 1
}
