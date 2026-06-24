import type { BaseQuestion } from '../../contracts/questions/base.js'
import type { MultipleChoiceSingle, MultipleChoiceMultiple, TrueFalse4Item } from '../../contracts/questions/types/choice.js'
import type { FlashcardDeckData } from '../../contracts/flashcard_deck.js'
import type { RecapData } from '../../contracts/recap.js'
import { mcSingleToH5P, mcMultipleToH5P } from './content-types/multi-choice.js'
import { tf4ItemToH5PArray } from './content-types/true-false.js'
import { flashcardsToH5P } from './content-types/flashcards.js'
import { recapToH5PSummary } from './content-types/summary.js'
import { buildH5PPackage } from './packager.js'

export class H5PExporter {
  async exportQuestion(question: BaseQuestion): Promise<Uint8Array | null> {
    switch (question.type) {
      case 'multiple_choice_single': {
        const content = mcSingleToH5P(question as MultipleChoiceSingle)
        return buildH5PPackage({ title: 'Multiple Choice', mainLibrary: 'H5P.MultiChoice', content })
      }
      case 'multiple_choice_multiple': {
        const content = mcMultipleToH5P(question as MultipleChoiceMultiple)
        return buildH5PPackage({ title: 'Multiple Choice', mainLibrary: 'H5P.MultiChoice', content })
      }
      case 'true_false_4item': {
        // Export first item only for single H5P.TrueFalse (one item = one H5P)
        const items = tf4ItemToH5PArray(question as TrueFalse4Item)
        if (!items[0]) return null
        return buildH5PPackage({ title: 'True/False', mainLibrary: 'H5P.TrueFalse', content: items[0] })
      }
      default:
        return null
    }
  }

  async exportFlashcards(deck: FlashcardDeckData): Promise<Uint8Array> {
    const content = flashcardsToH5P(deck)
    return buildH5PPackage({ title: deck.title, mainLibrary: 'H5P.Flashcards', content })
  }

  async exportRecapSummary(recap: RecapData): Promise<Uint8Array> {
    const content = recapToH5PSummary(recap)
    return buildH5PPackage({ title: recap.title, mainLibrary: 'H5P.Summary', content })
  }
}

export const h5pExporter = new H5PExporter()
