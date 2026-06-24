import type { BaseQuestion } from '../../contracts/questions/base.js'
import type { MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item } from '../../contracts/questions/types/choice.js'
import type { ShortAnswer } from '../../contracts/questions/types/text-entry.js'
import type { Essay } from '../../contracts/questions/types/open.js'

// Google Forms API — batchUpdate request item shape
export interface FormsItem {
  title:        string
  questionItem: {
    question: {
      required: boolean
      grading?: {
        pointValue:     number
        correctAnswers?: { answers: Array<{ value: string }> }
        whenRight?:     { text: string }
        whenWrong?:     { text: string }
      }
      choiceQuestion?:    ChoiceQuestion
      textQuestion?:      { paragraph: boolean }
      scaleQuestion?:     never
    }
  }
}

interface ChoiceQuestion {
  type:    'RADIO' | 'CHECKBOX' | 'DROP_DOWN'
  options: Array<{ value: string; isOther?: boolean }>
  shuffle: boolean
}

export function questionToFormsItem(q: BaseQuestion, pointValue = 1): FormsItem | null {
  switch (q.type) {
    case 'multiple_choice_single':
      return mcSingleToFormsItem(q as MultipleChoiceSingle, pointValue)
    case 'multiple_choice_multiple':
      return mcMultipleToFormsItem(q as MultipleChoiceMultiple, pointValue)
    case 'true_false_4item':
      return tf4ItemToFormsItem(q as TrueFalse4Item, pointValue)
    case 'short_answer':
      return shortAnswerToFormsItem(q as ShortAnswer, pointValue)
    case 'essay':
      return essayToFormsItem(q as Essay)
    default:
      return null
  }
}

function mcSingleToFormsItem(q: MultipleChoiceSingle, pointValue: number): FormsItem {
  const correct = q.options.find(o => o.isCorrect)
  return {
    title: q.stem,
    questionItem: {
      question: {
        required: true,
        grading: {
          pointValue,
          correctAnswers: correct ? { answers: [{ value: correct.text }] } : undefined,
          whenRight: { text: 'Correct!' },
          whenWrong: { text: 'Incorrect' },
        },
        choiceQuestion: {
          type:    'RADIO',
          options: q.options.map(o => ({ value: o.text })),
          shuffle: true,
        },
      },
    },
  }
}

function mcMultipleToFormsItem(q: MultipleChoiceMultiple, pointValue: number): FormsItem {
  const corrects = q.options.filter(o => o.isCorrect).map(o => ({ value: o.text }))
  return {
    title: q.stem,
    questionItem: {
      question: {
        required: true,
        grading: {
          pointValue,
          correctAnswers: { answers: corrects },
          whenRight: { text: 'Correct!' },
          whenWrong: { text: 'Incorrect' },
        },
        choiceQuestion: {
          type:    'CHECKBOX',
          options: q.options.map(o => ({ value: o.text })),
          shuffle: true,
        },
      },
    },
  }
}

function tf4ItemToFormsItem(q: TrueFalse4Item, pointValue: number): FormsItem {
  // Represent as CHECKBOX: "Select all TRUE statements"
  const corrects = q.items.filter(i => i.isTrue).map(i => ({ value: i.text }))
  return {
    title: q.stem + ' (Select all TRUE statements)',
    questionItem: {
      question: {
        required: true,
        grading: {
          pointValue,
          correctAnswers: { answers: corrects },
        },
        choiceQuestion: {
          type:    'CHECKBOX',
          options: q.items.map(i => ({ value: i.text })),
          shuffle: false,
        },
      },
    },
  }
}

function shortAnswerToFormsItem(q: ShortAnswer, pointValue: number): FormsItem {
  return {
    title: q.stem,
    questionItem: {
      question: {
        required: true,
        grading: {
          pointValue,
          correctAnswers: {
            answers: [q.correctAnswer, ...(q.acceptableAnswers ?? [])].map(a => ({ value: a })),
          },
        },
        textQuestion: { paragraph: false },
      },
    },
  }
}

function essayToFormsItem(q: Essay): FormsItem {
  return {
    title: q.prompt,
    questionItem: {
      question: {
        required: true,
        textQuestion: { paragraph: true },
      },
    },
  }
}
