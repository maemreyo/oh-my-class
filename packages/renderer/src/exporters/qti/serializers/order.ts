import type { IQTISerializer } from '../types.js'
import type { OrderQuestion } from '../../../contracts/questions/types/order.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const orderSerializer: IQTISerializer<OrderQuestion> = {
  serialize(question): string {
    const maxPoints = question.scoring?.pointsTotal ?? 1
    const items = getOrderItems(question)

    const sorted = [...items].sort((a, b) => a.position - b.position)
    const correct = sorted.map(i => i.id)

    const choices = items
      .map(i => `      <simpleChoice identifier="${escapeXml(i.id)}">${escapeXml(i.text)}</simpleChoice>`)
      .join('\n')

    return assessmentItem(question.id, question.id, [
      responseDeclaration('RESPONSE', 'ordered', 'identifier', correct),
      outcomeDeclaration(maxPoints),
      `  <itemBody>
    <orderInteraction responseIdentifier="RESPONSE" shuffle="true">
${choices}
    </orderInteraction>
  </itemBody>`,
    ].join('\n'))
  },
}

function getOrderItems(q: OrderQuestion): Array<{ id: string; text: string; position: number }> {
  switch (q.type) {
    case 'ordering':
      return q.items.map(i => ({ id: String(i.id), text: i.text, position: i.correctPosition }))
    case 'tense_timeline':
      return q.events.map((e, i) => ({ id: `E${i}`, text: `${e.time}: ${e.label}`, position: i }))
    case 'vocabulary_scaffolded':
      return q.stages.map((s, i) => ({ id: `S${i}`, text: s.stage, position: i }))
    default:
      return []
  }
}
