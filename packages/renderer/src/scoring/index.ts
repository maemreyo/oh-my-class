export type { ScoringStrategy, ScoreResult, BreakdownItem } from './types.js'

export { allOrNothing } from './strategies/all-or-nothing.js'
export type { AllOrNothingResponse } from './strategies/all-or-nothing.js'

export { partialCredit } from './strategies/partial-credit.js'
export type { PartialCreditResponse } from './strategies/partial-credit.js'

export { vietnameseTF2025, MOET_SCALE } from './strategies/vietnamese-tf-2025.js'
export type { TFResponse } from './strategies/vietnamese-tf-2025.js'

export { rubricScoring } from './strategies/rubric.js'
export type { RubricResponse, RubricQuestion } from './strategies/rubric.js'
