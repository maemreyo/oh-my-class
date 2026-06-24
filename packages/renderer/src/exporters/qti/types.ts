import type { BaseQuestion } from '../../contracts/questions/base.js'

export interface IQTISerializer<Q extends BaseQuestion = BaseQuestion> {
  // Returns QTI v3.0 assessmentItem XML string for a single question
  serialize(question: Q): string
}

