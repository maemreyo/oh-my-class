import type { BaseQuestion } from '@oh-my-class/renderer/contracts/questions/base.js'
import type {
  MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item,
} from '@oh-my-class/renderer/contracts/questions/types/choice.js'
import type { ShortAnswer, Cloze } from '@oh-my-class/renderer/contracts/questions/types/text-entry.js'
import type { Matching } from '@oh-my-class/renderer/contracts/questions/types/match.js'
import type { Essay } from '@oh-my-class/renderer/contracts/questions/types/open.js'
import type { QuizData } from '@oh-my-class/renderer/contracts/quiz.js'

function escapeGift(s: string): string {
  return s
    .replace(/\\/g, '\\\\')
    .replace(/~/g, '\\~')
    .replace(/=/g, '\\=')
    .replace(/\{/g, '\\{')
    .replace(/\}/g, '\\}')
    .replace(/#/g, '\\#')
}

function serializeMCSingle(q: MultipleChoiceSingle): string {
  const opts = q.options.map(o =>
    `  ${o.isCorrect ? '=' : '~'}${escapeGift(o.text)}`
  ).join('\n')
  return `::${q.id}::[html]${escapeGift(q.stem)}{\n${opts}\n}`
}

function serializeMCMultiple(q: MultipleChoiceMultiple): string {
  const opts = q.options.map(o => {
    const correctCount = q.options.filter(x => x.isCorrect).length
    const pct = correctCount > 0 ? Math.round(100 / correctCount) : 0
    return `  ${o.isCorrect ? `%${pct}%` : '~'}${escapeGift(o.text)}`
  }).join('\n')
  return `::${q.id}::[html]${escapeGift(q.stem)}{\n${opts}\n}`
}

function serializeTrueFalse4(q: TrueFalse4Item): string {
  // Render as multiple individual true/false items
  return q.items.map((item, i) =>
    `::${q.id}-${item.id}::[html]${escapeGift(item.text)}{ ${item.isTrue ? 'TRUE' : 'FALSE'} }`
  ).join('\n\n')
}

function serializeShortAnswer(q: ShortAnswer): string {
  const answers = [q.correctAnswer, ...(q.acceptableAnswers ?? [])].map(a => `  =${escapeGift(a)}`).join('\n')
  return `::${q.id}::[html]${escapeGift(q.stem)}{\n${answers}\n}`
}

function serializeCloze(q: Cloze): string {
  const passage = escapeGift(q.passage)
  const answers = q.blanks.map(b => `  =${escapeGift(b.correctAnswer)}`).join('\n')
  return `::${q.id}::[html]${passage}{\n${answers}\n}`
}

function serializeMatching(q: Matching): string {
  const pairs = q.correctMatches.map(m => {
    const left  = q.leftColumn.find(l => l.id === m.left)?.text  ?? m.left
    const right = q.rightColumn.find(r => r.id === m.right)?.text ?? m.right
    return `  =${escapeGift(left)}->${escapeGift(right)}`
  }).join('\n')
  return `::${q.id}::[html]${escapeGift(q.instructions)}{\n${pairs}\n}`
}

function serializeEssay(q: Essay): string {
  return `::${q.id}::[html]${escapeGift(q.prompt)}{ }`
}

function serializeQuestion(q: BaseQuestion): string | null {
  switch (q.type) {
    case 'multiple_choice_single':   return serializeMCSingle(q as MultipleChoiceSingle)
    case 'multiple_choice_multiple': return serializeMCMultiple(q as MultipleChoiceMultiple)
    case 'true_false_4item':         return serializeTrueFalse4(q as TrueFalse4Item)
    case 'short_answer':             return serializeShortAnswer(q as ShortAnswer)
    case 'cloze':                    return serializeCloze(q as Cloze)
    case 'matching':                 return serializeMatching(q as Matching)
    case 'essay':                    return serializeEssay(q as Essay)
    default:                         return null
  }
}

export class GIFTExporter {
  /**
   * Export an array of questions to Moodle GIFT format (.txt).
   * Unsupported question types are silently skipped.
   */
  export(questions: BaseQuestion[], category?: string): string {
    const lines: string[] = []
    if (category) {
      lines.push(`$CATEGORY: ${category}`)
      lines.push('')
    }
    for (const q of questions) {
      const gift = serializeQuestion(q)
      if (gift) {
        lines.push(gift)
        lines.push('')
      }
    }
    return lines.join('\n')
  }

  exportQuiz(quiz: QuizData): string {
    const category = quiz.title.replace(/\s+/g, '_')
    const lines: string[] = [`$CATEGORY: ${category}`, '']
    for (const q of quiz.questions) {
      const opts = q.options.map(o =>
        `  ${o.label === q.answer ? '=' : '~'}${escapeGift(o.text)}`
      ).join('\n')
      lines.push(`::${q.id}::[html]${escapeGift(q.prompt)}{\n${opts}\n}`)
      lines.push('')
    }
    return lines.join('\n')
  }
}

export const giftExporter = new GIFTExporter()
