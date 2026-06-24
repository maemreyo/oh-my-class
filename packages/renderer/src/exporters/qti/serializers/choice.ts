import type { IQTISerializer } from '../types.js'
import type { ChoiceQuestion, MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item } from '../../../contracts/questions/types/choice.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, simpleChoice, escapeXml } from '../base.js'

export const choiceSerializer: IQTISerializer<ChoiceQuestion> = {
  serialize(question): string {
    switch (question.type) {
      case 'multiple_choice_single':  return serializeMCSingle(question)
      case 'multiple_choice_multiple': return serializeMCMultiple(question)
      case 'true_false_4item':        return serializeTF4(question)
      case 'phonics':                 return serializePhonics(question as ChoiceQuestion)
      default:
        throw new Error(`choiceSerializer: unknown type "${(question as { type: string }).type}"`)
    }
  },
}

function serializeMCSingle(q: MultipleChoiceSingle): string {
  const correctId = q.options.find(o => o.isCorrect)?.id ?? ''
  const choices   = q.options.map(o => simpleChoice(o.id, o.text)).join('\n')
  return assessmentItem(q.id, q.id, [
    responseDeclaration('RESPONSE', 'single', 'identifier', [correctId]),
    outcomeDeclaration(q.scoring?.pointsTotal ?? 1),
    `  <itemBody>
    <p>${escapeXml(q.stem)}</p>
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="true" maxChoices="1">
${choices}
    </choiceInteraction>
  </itemBody>`,
  ].join('\n'))
}

function serializeMCMultiple(q: MultipleChoiceMultiple): string {
  const correctIds = q.options.filter(o => o.isCorrect).map(o => o.id)
  const choices    = q.options.map(o => simpleChoice(o.id, o.text)).join('\n')
  return assessmentItem(q.id, q.id, [
    responseDeclaration('RESPONSE', 'multiple', 'identifier', correctIds),
    outcomeDeclaration(q.scoring?.pointsTotal ?? 1),
    `  <itemBody>
    <p>${escapeXml(q.stem)}</p>
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="true" maxChoices="0">
${choices}
    </choiceInteraction>
  </itemBody>`,
  ].join('\n'))
}

function serializeTF4(q: TrueFalse4Item): string {
  const items = q.items.map((item, i) =>
    `      <simpleChoice identifier="tf${i}_true">${escapeXml(item.text)} — True</simpleChoice>
      <simpleChoice identifier="tf${i}_false">${escapeXml(item.text)} — False</simpleChoice>`
  ).join('\n')
  const correct = q.items.map((item, i) => item.isTrue ? `tf${i}_true` : `tf${i}_false`)
  return assessmentItem(q.id, q.id, [
    responseDeclaration('RESPONSE', 'multiple', 'identifier', correct),
    outcomeDeclaration(1.0),
    `  <itemBody>
    <p>${escapeXml(q.stem)}</p>
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="0">
${items}
    </choiceInteraction>
  </itemBody>`,
  ].join('\n'))
}

function serializePhonics(q: ChoiceQuestion): string {
  return assessmentItem(q.id, q.id, [
    responseDeclaration('RESPONSE', 'single', 'identifier', []),
    outcomeDeclaration(q.scoring?.pointsTotal ?? 1),
    `  <itemBody><p>Phonics question — see original data</p></itemBody>`,
  ].join('\n'))
}
