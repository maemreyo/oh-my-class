import type { BaseQuestion } from '@oh-my-class/renderer/contracts/questions/base.js'
import type { QuizData } from '@oh-my-class/renderer/contracts/quiz.js'
import { questionToFormsItem, type FormsItem } from './question-mapper.js'
import { createGoogleFormsClient, type BatchUpdateRequest } from './client.js'

export { getAuthUrl, exchangeCode, refreshAccessToken } from './auth.js'
export { questionToFormsItem, type FormsItem } from './question-mapper.js'
export { createGoogleFormsClient } from './client.js'

export interface GoogleFormsExportResult {
  formId:       string
  responderUri: string
  itemCount:    number
}

export class GoogleFormsExporter {
  private client: ReturnType<typeof createGoogleFormsClient>

  constructor(accessToken: string) {
    this.client = createGoogleFormsClient({ accessToken })
  }

  /**
   * Build a batchUpdate requests array from questions (without API call).
   * Useful for testing the payload without OAuth.
   */
  buildBatchUpdateRequests(questions: BaseQuestion[], pointsPerQuestion = 1): BatchUpdateRequest[] {
    const requests: BatchUpdateRequest[] = []
    let index = 0
    for (const q of questions) {
      const item = questionToFormsItem(q, pointsPerQuestion)
      if (item) {
        requests.push({ createItem: { item, location: { index: index++ } } })
      }
    }
    return requests
  }

  async exportQuestions(
    title: string,
    questions: BaseQuestion[],
    pointsPerQuestion = 1,
  ): Promise<GoogleFormsExportResult> {
    const { formId, responderUri } = await this.client.createForm(title)
    const requests = this.buildBatchUpdateRequests(questions, pointsPerQuestion)
    if (requests.length > 0) {
      await this.client.batchUpdate(formId, requests)
    }
    return { formId, responderUri, itemCount: requests.length }
  }
}
