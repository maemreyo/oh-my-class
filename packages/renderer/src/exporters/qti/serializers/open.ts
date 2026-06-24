import type { IQTISerializer } from '../types.js'
import type { OpenQuestion } from '../../../contracts/questions/types/open.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const openSerializer: IQTISerializer<OpenQuestion> = {
  serialize(question): string {
    const maxPoints = question.scoring?.pointsTotal ?? 1
    const prompt = getPrompt(question)

    return assessmentItem(question.id, question.id, [
      responseDeclaration('RESPONSE', 'single', 'string', []),
      outcomeDeclaration(maxPoints),
      `  <itemBody>
    <p>${escapeXml(prompt)}</p>
    <extendedTextInteraction responseIdentifier="RESPONSE"${getExpectedLines(question)}/>
  </itemBody>`,
    ].join('\n'))
  },
}

function getPrompt(q: OpenQuestion): string {
  switch (q.type) {
    case 'essay':       return q.prompt
    case 'paraphrase':  return q.originalSentence
    case 'translation': return q.sourceText
    case 'lab_report':  return q.experimentTitle
    case 'drawing':     return q.instructions
    case 'performance': return q.task
    case 'dictation':   return q.text
    default:            return ''
  }
}

function getExpectedLines(q: OpenQuestion): string {
  if (q.type === 'essay' && q.wordLimit) {
    return ` expectedLines="${Math.ceil(q.wordLimit.max / 10)}"`
  }
  return ''
}
