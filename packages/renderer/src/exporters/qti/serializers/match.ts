import type { IQTISerializer } from '../types.js'
import type { MatchQuestion } from '../../../contracts/questions/types/match.js'
import { assessmentItem, responseDeclaration, outcomeDeclaration, escapeXml } from '../base.js'

export const matchSerializer: IQTISerializer<MatchQuestion> = {
  serialize(question): string {
    const maxPoints = question.scoring?.pointsTotal ?? 1
    const { left, right, correct } = getMatchData(question)

    const sourceChoices = left
      .map(item => `      <simpleAssociableChoice identifier="${escapeXml(item.id)}" matchMax="1">${escapeXml(item.text)}</simpleAssociableChoice>`)
      .join('\n')

    const targetChoices = right
      .map(item => `      <simpleAssociableChoice identifier="${escapeXml(item.id)}" matchMax="1">${escapeXml(item.text)}</simpleAssociableChoice>`)
      .join('\n')

    const correctPairs = correct.map(p => `${p.left} ${p.right}`)

    return assessmentItem(question.id, question.id, [
      responseDeclaration('RESPONSE', 'multiple', 'directedPair', correctPairs),
      outcomeDeclaration(maxPoints),
      `  <itemBody>
    <matchInteraction responseIdentifier="RESPONSE" shuffle="true" maxAssociations="${correct.length}">
      <simpleMatchSet>
${sourceChoices}
      </simpleMatchSet>
      <simpleMatchSet>
${targetChoices}
      </simpleMatchSet>
    </matchInteraction>
  </itemBody>`,
    ].join('\n'))
  },
}

function getMatchData(q: MatchQuestion): {
  left: Array<{ id: string; text: string }>
  right: Array<{ id: string; text: string }>
  correct: Array<{ left: string; right: string }>
} {
  switch (q.type) {
    case 'matching':
      return { left: q.leftColumn, right: q.rightColumn, correct: q.correctMatches }
    case 'matching_vocabulary':
      return {
        left: q.leftColumn,
        right: q.rightColumn,
        correct: q.leftColumn.map((item, i) => ({ left: item.id, right: q.rightColumn[i]?.id ?? '' })),
      }
    case 'collocation':
      return {
        left:    q.leftItems.map((t, i) => ({ id: `L${i}`, text: t })),
        right:   q.rightItems.map((t, i) => ({ id: `R${i}`, text: t })),
        correct: q.correctPairs.map(p => ({
          left:  `L${q.leftItems.indexOf(p.left)}`,
          right: `R${q.rightItems.indexOf(p.right)}`,
        })),
      }
    case 'idioms':
      return {
        left:    q.activity.idioms.map((e, i) => ({ id: `I${i}`, text: e.idiom })),
        right:   q.activity.idioms.map((e, i) => ({ id: `M${i}`, text: e.meaning })),
        correct: q.activity.idioms.map((_, i) => ({ left: `I${i}`, right: `M${i}` })),
      }
    case 'word_analysis':
      return {
        left:    q.morphemes.map((m, i) => ({ id: `P${i}`, text: m.part })),
        right:   q.morphemes.map((m, i) => ({ id: `T${i}`, text: m.meaning })),
        correct: q.morphemes.map((_, i) => ({ left: `P${i}`, right: `T${i}` })),
      }
    default:
      return { left: [], right: [], correct: [] }
  }
}
