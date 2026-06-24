import type { IQTISerializer } from '../types.js'
import type { MultimediaQuestion, SubmissionInfo } from '../../../contracts/questions/types/multimedia.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const multimediaSerializer: IQTISerializer<MultimediaQuestion> = {
  serialize(question): string {
    const maxPoints = question.scoring?.pointsTotal ?? 1
    const { prompt, accept } = getUploadData(question)
    const submissionNote = getSubmissionNote(question)

    return assessmentItem(question.id, question.id, [
      responseDeclaration('RESPONSE', 'single', 'file', []),
      outcomeDeclaration(maxPoints),
      `  <itemBody>
    <p>${escapeXml(prompt)}</p>
    ${submissionNote ? `<p><em>${escapeXml(submissionNote)}</em></p>` : ''}
    <uploadInteraction responseIdentifier="RESPONSE" type="${accept}"/>
  </itemBody>`,
    ].join('\n'))
  },
}

function getUploadData(q: MultimediaQuestion): { prompt: string; accept: string } {
  switch (q.type) {
    case 'multimedia_video':
      return { prompt: q.instructions, accept: 'video/*' }
    case 'multimedia_audio':
      return { prompt: q.instructions, accept: 'audio/*' }
    case 'multimedia_photo':
      return { prompt: q.instructions, accept: 'image/*' }
    case 'experiment_documentation':
      return { prompt: q.experiment.title, accept: 'image/*,video/*' }
    case 'parent_child_activity':
      return { prompt: q.title, accept: 'image/*,video/*' }
    case 'field_trip_journal':
      return { prompt: q.destination, accept: 'image/*,application/pdf' }
    case 'art_project':
      return { prompt: q.prompt, accept: 'image/*,video/*' }
    default:
      return { prompt: '', accept: '*/*' }
  }
}

function getSubmissionNote(q: MultimediaQuestion): string {
  // All multimedia union members declare submission?: SubmissionInfo
  const withSubmission = q as typeof q & { submission?: SubmissionInfo }
  const submission     = withSubmission.submission
  if (!submission) return ''
  const names: Record<string, string> = {
    google_classroom: 'Google Classroom',
    seesaw:           'Seesaw',
    microsoft_teams:  'Microsoft Teams for Education',
    email:            'Email',
  }
  const platforms = submission.platforms.map(p => names[p] ?? p).join(' / ')
  return `Submit via: ${platforms}`
}
