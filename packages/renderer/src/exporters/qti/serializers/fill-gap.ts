import type { IQTISerializer } from '../types.js'
import type { FillGapQuestion } from '../../../contracts/questions/types/fill-gap.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const fillGapSerializer: IQTISerializer<FillGapQuestion> = {
  serialize(question): string {
    const maxPoints = question.scoring?.pointsTotal ?? 1
    const blanks = getBlanks(question)
    const correctResponses = blanks.map(b => b.correct)

    const choiceOptions = blanks
      .flatMap(b => b.options)
      .filter((v, i, arr) => arr.indexOf(v) === i)

    const inlineChoices = choiceOptions
      .map(opt => `        <inlineChoice identifier="${escapeXml(opt)}">${escapeXml(opt)}</inlineChoice>`)
      .join('\n')

    const bodyText = blanks.map((b, i) => `
    <inlineChoiceInteraction responseIdentifier="RESPONSE_${i}" shuffle="true">
${inlineChoices}
    </inlineChoiceInteraction>`).join('')

    const responseDeclarations = blanks
      .map((b, i) =>
        responseDeclaration(`RESPONSE_${i}`, 'single', 'identifier', [b.correct])
      ).join('\n')

    return assessmentItem(question.id, question.id, [
      responseDeclarations,
      outcomeDeclaration(maxPoints),
      `  <itemBody>
    <p>${escapeXml(getPassage(question))}</p>${bodyText}
  </itemBody>`,
    ].join('\n'))
  },
}

function getPassage(q: FillGapQuestion): string {
  switch (q.type) {
    case 'fill_blank_wordbank': return q.context
    case 'cloze_mixed':        return q.passage
    case 'dialogue_completion': return q.context
    default:                   return ''
  }
}

function getBlanks(q: FillGapQuestion): Array<{ correct: string; options: string[] }> {
  switch (q.type) {
    case 'fill_blank_wordbank':
      return q.blanks.map(b => ({
        correct: b.correctAnswer,
        options: [...q.wordBank, ...q.distractors],
      }))
    case 'cloze_mixed':
      return q.blanks.map(b => ({
        correct: b.correctAnswer,
        options: q.wordBank ?? [b.correctAnswer],
      }))
    case 'dialogue_completion':
      return q.blanks.map(b => ({
        correct: b.expectedAnswer,
        options: [b.expectedAnswer],
      }))
    default:
      return []
  }
}
