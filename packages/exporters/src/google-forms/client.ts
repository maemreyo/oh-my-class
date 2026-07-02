import type { FormsItem } from './question-mapper.js'

const FORMS_API = 'https://forms.googleapis.com/v1/forms'

export interface GoogleFormsClient {
  createForm(title: string): Promise<{ formId: string; responderUri: string }>
  batchUpdate(formId: string, requests: BatchUpdateRequest[]): Promise<void>
  listResponses(formId: string): Promise<FormsResponse[]>
}

export interface FormsTextAnswer {
  value: string
}

export interface FormsAnswerGrade {
  score?: number
  correct?: boolean
}

export interface FormsAnswer {
  questionId: string
  grade?: FormsAnswerGrade
  textAnswers?: { answers: readonly FormsTextAnswer[] }
}

export interface FormsResponse {
  responseId: string
  respondentEmail?: string
  createTime: string
  answers: Record<string, FormsAnswer>
}

export interface BatchUpdateRequest {
  createItem: {
    item:     FormsItem
    location: { index: number }
  }
}

export interface GoogleFormsClientConfig {
  accessToken: string
}

export function createGoogleFormsClient(config: GoogleFormsClientConfig): GoogleFormsClient {
  const headers = {
    'Authorization': `Bearer ${config.accessToken}`,
    'Content-Type':  'application/json',
  }

  return {
    async createForm(title: string) {
      const res = await fetch(FORMS_API, {
        method:  'POST',
        headers,
        body:    JSON.stringify({ info: { title } }),
      })
      if (!res.ok) throw new Error(`Forms API createForm failed: ${res.status}`)
      return res.json() as Promise<{ formId: string; responderUri: string }>
    },

    async batchUpdate(formId: string, requests: BatchUpdateRequest[]) {
      const res = await fetch(`${FORMS_API}/${formId}:batchUpdate`, {
        method:  'POST',
        headers,
        body:    JSON.stringify({ requests }),
      })
      if (!res.ok) throw new Error(`Forms API batchUpdate failed: ${res.status}`)
    },

    async listResponses(formId: string) {
      const res = await fetch(`${FORMS_API}/${formId}/responses`, {
        method: 'GET',
        headers,
      })
      if (!res.ok) throw new Error(`Forms API listResponses failed: ${res.status}`)
      const data = await res.json() as { responses?: FormsResponse[] }
      return data.responses ?? []
    },
  }
}
