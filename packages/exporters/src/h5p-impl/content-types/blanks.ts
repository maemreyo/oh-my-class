import type { Cloze, FillBlankWordBank } from '@oh-my-class/renderer/contracts/questions/types/fill-gap.js'

export interface H5PBlanksContent {
  text:     string   // passage with *blank* markers like: "Hello *world*!"
  behaviour: {
    enableRetry:         boolean
    enableSolutionsButton: boolean
    caseSensitive:       boolean
  }
  l10n: { checkAnswer: string; showSolution: string; tryAgain: string }
}

function buildBlanksText(passage: string, blanks: Array<{ id: number; correctAnswer: string }>): string {
  // Replace ___ or blank markers sequentially with *answer* syntax
  let result = passage
  for (const blank of blanks) {
    result = result.replace('___', `*${blank.correctAnswer}*`)
  }
  return `<p>${result}</p>`
}

export function clozeToH5PBlanks(q: Cloze): H5PBlanksContent {
  return {
    text:     buildBlanksText(q.passage, q.blanks),
    behaviour: {
      enableRetry:           true,
      enableSolutionsButton: true,
      caseSensitive:         q.caseSensitive,
    },
    l10n: { checkAnswer: 'Check', showSolution: 'Show solution', tryAgain: 'Retry' },
  }
}

export function fillBlankToH5PBlanks(q: FillBlankWordBank): H5PBlanksContent {
  return {
    text:     buildBlanksText(q.context, q.blanks),
    behaviour: {
      enableRetry:           true,
      enableSolutionsButton: true,
      caseSensitive:         false,
    },
    l10n: { checkAnswer: 'Check', showSolution: 'Show solution', tryAgain: 'Retry' },
  }
}
