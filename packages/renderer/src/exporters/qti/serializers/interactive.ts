import type { IQTISerializer } from '../types.js'
import type { InteractiveQuestion } from '../../../contracts/questions/types/interactive.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const interactiveSerializer: IQTISerializer<InteractiveQuestion> = {
  serialize(question): string {
    const maxPoints = question.scoring?.pointsTotal ?? 1
    const { prompt, pairs } = getAssocData(question)

    if (pairs.length === 0) {
      return assessmentItem(question.id, question.id, [
        responseDeclaration('RESPONSE', 'single', 'string', []),
        outcomeDeclaration(maxPoints),
        `  <itemBody><p>${escapeXml(prompt)}</p><extendedTextInteraction responseIdentifier="RESPONSE"/></itemBody>`,
      ].join('\n'))
    }

    const sources = [...new Set(pairs.map(p => p.source))]
    const targets = [...new Set(pairs.map(p => p.target))]

    const sourceChoices = sources
      .map(s => `      <simpleAssociableChoice identifier="${escapeXml(s)}" matchMax="1">${escapeXml(s)}</simpleAssociableChoice>`)
      .join('\n')
    const targetChoices = targets
      .map(t => `      <simpleAssociableChoice identifier="${escapeXml(t)}" matchMax="1">${escapeXml(t)}</simpleAssociableChoice>`)
      .join('\n')

    const correct = pairs.map(p => `${p.source} ${p.target}`)

    return assessmentItem(question.id, question.id, [
      responseDeclaration('RESPONSE', 'multiple', 'directedPair', correct),
      outcomeDeclaration(maxPoints),
      `  <itemBody>
    <p>${escapeXml(prompt)}</p>
    <associateInteraction responseIdentifier="RESPONSE" shuffle="true" maxAssociations="${pairs.length}">
      <simpleMatchSet>
${sourceChoices}
      </simpleMatchSet>
      <simpleMatchSet>
${targetChoices}
      </simpleMatchSet>
    </associateInteraction>
  </itemBody>`,
    ].join('\n'))
  },
}

function getAssocData(q: InteractiveQuestion): {
  prompt: string
  pairs: Array<{ source: string; target: string }>
} {
  switch (q.type) {
    case 'drag_and_drop':
      return {
        prompt: q.instructions,
        pairs: q.draggables
          .filter(d => !d.isDistractor)
          .map(d => ({ source: d.text, target: d.correctZone })),
      }
    case 'data_interpretation':
      return { prompt: q.dataDisplay.title, pairs: [] }
    case 'step_by_step_math':
      return { prompt: q.problem, pairs: [] }
    case 'geometric_proof':
      return { prompt: q.prove, pairs: [] }
    case 'branching_scenario':
      return { prompt: q.initialPrompt, pairs: [] }
    case 'coding_exercise':
      return { prompt: q.question, pairs: [] }
    case 'financial_literacy':
      return { prompt: q.scenario, pairs: [] }
    case 'measurement':
      return { prompt: q.questions[0]?.stem ?? '', pairs: [] }
    default:
      return { prompt: '', pairs: [] }
  }
}
