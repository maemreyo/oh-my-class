import type { FlashcardDeckData, Flashcard } from '../../contracts/flashcard_deck.js'

/**
 * FlashcardTSVExporter — tab-separated values for Quizlet and Anki import.
 *
 * Format: front\tback\ttags (one card per line)
 * Quizlet: import with tab delimiter, no card separator
 * Anki:    import with tab delimiter, Tags field = column 3
 */
export class FlashcardTSVExporter {
  export(cards: Flashcard[], tags: string[] = []): string {
    const tagStr = tags.join(' ')
    return cards.map(c => {
      const front = sanitizeField(c.front)
      const back  = sanitizeField(c.back)
      return tagStr ? `${front}\t${back}\t${tagStr}` : `${front}\t${back}`
    }).join('\n')
  }

  exportDeck(deck: FlashcardDeckData): string {
    const tags = [deck.subject, deck.gradeLevel].filter(Boolean)
    return this.export(deck.cards, tags)
  }
}

function sanitizeField(text: string): string {
  // Escape tabs and newlines so they don't break TSV structure
  return text.replace(/\t/g, ' ').replace(/\n/g, '<br>')
}

export const flashcardTSVExporter = new FlashcardTSVExporter()
