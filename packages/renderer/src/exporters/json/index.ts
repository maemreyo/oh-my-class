import type { BaseQuestion } from '../../contracts/questions/base.js'

export interface QuestionBank {
  version:     string
  exportedAt:  string
  totalCount:  number
  questions:   BaseQuestion[]
}

// QB2: question bank → JSON (no Elo/spaced-repetition, LMS responsibility)
export class JSONExporter {
  export(questions: BaseQuestion[]): QuestionBank {
    return {
      version:    '1.0',
      exportedAt: new Date().toISOString(),
      totalCount: questions.length,
      questions,
    }
  }

  serialize(questions: BaseQuestion[]): string {
    return JSON.stringify(this.export(questions), null, 2)
  }
}

export const jsonExporter = new JSONExporter()
