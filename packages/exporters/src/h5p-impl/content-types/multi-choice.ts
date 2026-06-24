import type { MultipleChoiceSingle, MultipleChoiceMultiple, MCOption } from '@oh-my-class/renderer/contracts/questions/types/choice.js'

export interface H5PMultiChoiceContent {
  question: string
  answers: Array<{
    text:      string
    correct:   boolean
    tipsAndFeedback: { tip: string; chosenFeedback: string; notChosenFeedback: string }
  }>
  behaviour: {
    enableRetry:         boolean
    enableSolutionsButton: boolean
    singleAnswer:        boolean
    randomAnswers:       boolean
  }
  UI: { checkAnswerButton: string; submitAnswerButton: string; showSolutionButton: string; tryAgainButton: string }
}

export function mcSingleToH5P(q: MultipleChoiceSingle): H5PMultiChoiceContent {
  return buildH5PMultiChoice(q.stem, q.options, true)
}

export function mcMultipleToH5P(q: MultipleChoiceMultiple): H5PMultiChoiceContent {
  return buildH5PMultiChoice(q.stem, q.options, false)
}

function buildH5PMultiChoice(stem: string, options: MCOption[], single: boolean): H5PMultiChoiceContent {
  return {
    question: `<p>${stem}</p>`,
    answers: options.map(o => ({
      text:    `<div>${o.text}</div>`,
      correct: o.isCorrect,
      tipsAndFeedback: { tip: '', chosenFeedback: '', notChosenFeedback: '' },
    })),
    behaviour: {
      enableRetry:           true,
      enableSolutionsButton: true,
      singleAnswer:          single,
      randomAnswers:         true,
    },
    UI: {
      checkAnswerButton:   'Check',
      submitAnswerButton:  'Submit',
      showSolutionButton:  'Show solution',
      tryAgainButton:      'Retry',
    },
  }
}
