import { describe, it, expect } from 'vitest'
import { FlashcardTSVExporter } from '../src/flashcard-tsv/index.js'
import type { Flashcard, FlashcardDeckData } from '@oh-my-class/renderer/contracts/flashcard_deck.js'

const exporter = new FlashcardTSVExporter()

const cards: Flashcard[] = [
  { id: 'c1', front: 'Hello',   back: 'Xin chào' },
  { id: 'c2', front: 'Goodbye', back: 'Tạm biệt' },
]

const deck: FlashcardDeckData = {
  title:      'English Greetings',
  subject:    'english',
  gradeLevel: '6',
  cards,
}

describe('FlashcardTSVExporter', () => {
  it('exports cards as tab-separated front/back', () => {
    const out = exporter.export(cards)
    const lines = out.split('\n')
    expect(lines).toHaveLength(2)
    expect(lines[0]).toBe('Hello\tXin chào')
    expect(lines[1]).toBe('Goodbye\tTạm biệt')
  })

  it('appends tags column when tags provided', () => {
    const out = exporter.export(cards, ['english', 'grade6'])
    const lines = out.split('\n')
    expect(lines[0]).toBe('Hello\tXin chào\tenglish grade6')
  })

  it('omits tags column when no tags', () => {
    const out = exporter.export(cards, [])
    expect(out.split('\n')[0].split('\t')).toHaveLength(2)
  })

  it('sanitises tabs in card content to spaces', () => {
    const tabCard: Flashcard[] = [{ id: 'x', front: 'A\tB', back: 'C\tD' }]
    const out = exporter.export(tabCard)
    expect(out).toBe('A B\tC D')
  })

  it('sanitises newlines in card content to <br>', () => {
    const nlCard: Flashcard[] = [{ id: 'x', front: 'Line1\nLine2', back: 'Back' }]
    const out = exporter.export(nlCard)
    expect(out).toBe('Line1<br>Line2\tBack')
  })

  it('exportDeck builds tags from subject and gradeLevel', () => {
    const out = exporter.exportDeck(deck)
    const firstLine = out.split('\n')[0]
    expect(firstLine).toContain('english')
    expect(firstLine).toContain('6')
  })

  it('exportDeck includes all cards', () => {
    const out = exporter.exportDeck(deck)
    expect(out.split('\n')).toHaveLength(2)
  })
})
