import type { FlashcardDeckData, Flashcard } from '@oh-my-class/renderer/contracts/flashcard_deck.js'

export interface H5PFlashcardsContent {
  description: string
  cards: Array<{
    text:  string   // front (question)
    answer: string  // back (answer)
    tip?:  string
  }>
  progressText: string
}

export function flashcardsToH5P(deck: FlashcardDeckData): H5PFlashcardsContent {
  return {
    description: deck.title,
    cards: deck.cards.map(c => ({
      text:   c.front,
      answer: c.back,
      tip:    c.hint,
    })),
    progressText: 'Card @card of @total',
  }
}
