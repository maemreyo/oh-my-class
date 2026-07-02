import type { BaseQuestion } from '@oh-my-class/renderer/contracts/questions/base.js'
import type { QuizData } from '@oh-my-class/renderer/contracts/quiz.js'
import { questionToFormsItem, type FormsItem } from './question-mapper.js'
import { createGoogleFormsClient, type BatchUpdateRequest, type FormsResponse } from './client.js'

export { getAuthUrl, exchangeCode, refreshAccessToken } from './auth.js'
export { questionToFormsItem, type FormsItem } from './question-mapper.js'
export { createGoogleFormsClient } from './client.js'

export interface GoogleFormsExportResult {
  formId:       string
  responderUri: string
  itemCount:    number
}

export interface FormsQuestionMapping {
  readonly questionId: string
  readonly kcIds: readonly string[]
}

export interface FormsCaptureInput {
  readonly classId: string
  readonly deliveryId: string
  readonly formId: string
  readonly teacherId: string
  readonly questionKcMap: Readonly<Record<string, FormsQuestionMapping>>
  readonly responses: readonly FormsResponse[]
  readonly essayScores?: Readonly<Record<string, number>>
}

export interface StudentAttemptPayload {
  readonly schema_version: 'student_attempt.v1'
  readonly attempt_id: string
  readonly student_pseudonym: string
  readonly question_id: string
  readonly kc_ids: readonly string[]
  readonly correct: boolean
  readonly score: number
  readonly timestamp: string
  readonly delivery_id: string
}

export interface PseudonymInput {
  readonly teacherId: string
  readonly classId: string
  readonly respondent: string
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

  async listResponses(formId: string): Promise<FormsResponse[]> {
    return this.client.listResponses(formId)
  }
}

export function normalizeFormsResponses(input: FormsCaptureInput): StudentAttemptPayload[] {
  return input.responses.flatMap((response) => Object.entries(response.answers).flatMap(([itemId, answer]) => {
    const mapping = input.questionKcMap[itemId]
    if (!mapping) return []
    const essayScore = input.essayScores?.[`${response.responseId}:${itemId}`]
    const score = clampScore(answer.grade?.score ?? essayScore ?? 0)
    const respondent = response.respondentEmail ?? response.responseId
    return [{
      schema_version: 'student_attempt.v1',
      attempt_id: `forms:${input.formId}:${response.responseId}:${itemId}`,
      student_pseudonym: pseudonymizeRespondent({
        teacherId: input.teacherId,
        classId: input.classId,
        respondent,
      }),
      question_id: mapping.questionId,
      kc_ids: mapping.kcIds,
      correct: answer.grade?.correct ?? score >= 0.6,
      score,
      timestamp: response.createTime,
      delivery_id: input.deliveryId,
    }]
  }))
}

export function pseudonymizeRespondent(input: PseudonymInput): string {
  const hash = fnv1a64(`${input.teacherId}:${input.classId}:${input.respondent.trim().toLowerCase()}`)
  return `sha256:${hash}`
}

function clampScore(value: number): number {
  return Math.min(1, Math.max(0, value))
}

function fnv1a64(value: string): string {
  let hash = 0xcbf29ce484222325n
  const prime = 0x100000001b3n
  const mask = 0xffffffffffffffffn
  for (const char of value) {
    hash ^= BigInt(char.codePointAt(0) ?? 0)
    hash = (hash * prime) & mask
  }
  return hash.toString(16).padStart(16, '0')
}
