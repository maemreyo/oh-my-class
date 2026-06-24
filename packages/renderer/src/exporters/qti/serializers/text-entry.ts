import type { IQTISerializer } from '../types.js'
import type { TextEntryQuestion } from '../../../contracts/questions/types/text-entry.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const textEntrySerializer: IQTISerializer<TextEntryQuestion> = {
  serialize(question): string {
    const stem = getStem(question)
    const correctAnswers = getCorrectAnswers(question)
    return assessmentItem(question.id, question.id, [
      responseDeclaration('RESPONSE', 'single', 'string', correctAnswers),
      outcomeDeclaration(question.scoring?.pointsTotal ?? 1),
      `  <itemBody>
    <p>${escapeXml(stem)}</p>
    <textEntryInteraction responseIdentifier="RESPONSE" expectedLength="200"/>
  </itemBody>`,
    ].join('\n'))
  },
}

function getStem(q: TextEntryQuestion): string {
  switch (q.type) {
    case 'cloze':                 return q.passage
    case 'short_answer':          return q.stem
    case 'grammar_transformation': return q.sourceSentence
    case 'reported_speech':        return q.directSpeech
    case 'passive_voice':          return q.activeSentence ?? q.passiveSentence ?? ''
    case 'conditional_builder':    return q.activities[0]?.stem ?? ''
    case 'error_correction':       return q.originalText
    case 'sentence_manipulation':  return q.inputSentences.join(' / ')
    default:                       return ''
  }
}

function getCorrectAnswers(q: TextEntryQuestion): string[] {
  switch (q.type) {
    case 'short_answer':
      return [q.correctAnswer, ...q.acceptableAnswers]
    case 'grammar_transformation':
      return [q.expectedAnswer, ...q.acceptableAnswers]
    case 'reported_speech':
      return [q.expectedAnswer]
    case 'passive_voice':
      return [q.expectedPassive ?? q.expectedActive ?? '']
    case 'error_correction':
      return [q.correctedAnswer]
    case 'sentence_manipulation':
      return [q.expectedOutput]
    default:
      return []
  }
}
