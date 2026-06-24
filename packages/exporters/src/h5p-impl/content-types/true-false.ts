import type { TrueFalse4Item } from '@oh-my-class/renderer/contracts/questions/types/choice.js'

export interface H5PTrueFalseContent {
  question: string
  correct:  'true' | 'false'
  behaviour: { enableRetry: boolean; enableSolutionsButton: boolean }
  l10n: { trueText: string; falseText: string }
}

export function tfItemToH5P(stem: string, isTrue: boolean): H5PTrueFalseContent {
  return {
    question: `<p>${stem}</p>`,
    correct:  isTrue ? 'true' : 'false',
    behaviour: { enableRetry: true, enableSolutionsButton: true },
    l10n:     { trueText: 'True', falseText: 'False' },
  }
}

export function tf4ItemToH5PArray(q: TrueFalse4Item): H5PTrueFalseContent[] {
  return q.items.map(item => tfItemToH5P(item.text, item.isTrue))
}
