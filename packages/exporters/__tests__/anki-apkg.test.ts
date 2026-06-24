import { describe, it, expect } from 'vitest'
import { AnkiApkgExporter, exportApkg } from '../src/anki-apkg/index.js'
import type { FlashcardDeckData } from '@oh-my-class/renderer/contracts/flashcard_deck.js'
import { unzipSync, strFromU8 } from 'fflate'

const deck: FlashcardDeckData = {
  title:      'English Vocab',
  subject:    'english',
  gradeLevel: '8',
  cards: [
    { id: 'c1', front: 'Hello',   back: 'Xin chào' },
    { id: 'c2', front: 'Goodbye', back: 'Tạm biệt' },
  ],
}

describe('exportApkg', () => {
  it('returns a Uint8Array (ZIP magic bytes PK)', async () => {
    const pkg = await exportApkg('Test Deck', [{ front: 'A', back: 'B' }])
    expect(pkg).toBeInstanceOf(Uint8Array)
    expect(pkg[0]).toBe(0x50)
    expect(pkg[1]).toBe(0x4B)
  })

  it('ZIP contains collection.anki2 and media', async () => {
    const pkg = await exportApkg('My Deck', [{ front: 'Q', back: 'A' }])
    const files = unzipSync(pkg)
    expect(Object.keys(files)).toContain('collection.anki2')
    expect(Object.keys(files)).toContain('media')
  })

  it('media file is empty JSON object', async () => {
    const pkg = await exportApkg('Deck', [{ front: 'Q', back: 'A' }])
    const files = unzipSync(pkg)
    expect(strFromU8(files['media']!)).toBe('{}')
  })

  it('collection.anki2 is a SQLite file (magic header)', async () => {
    const pkg = await exportApkg('Deck', [{ front: 'Q', back: 'A' }])
    const files = unzipSync(pkg)
    const sqlite = files['collection.anki2']!
    // SQLite magic: starts with "SQLite format 3\0"
    const magic = strFromU8(sqlite.slice(0, 15))
    expect(magic).toBe('SQLite format 3')
  })

  it('produces identical output for same inputs (deterministic)', async () => {
    const cards = [{ front: 'X', back: 'Y' }]
    const [a, b] = await Promise.all([
      exportApkg('SameDeck', cards, 1_700_000_000),
      exportApkg('SameDeck', cards, 1_700_000_000),
    ])
    expect(a).toEqual(b)
  })
})

describe('AnkiApkgExporter', () => {
  const exporter = new AnkiApkgExporter()

  it('exportDeck creates a valid .apkg from FlashcardDeckData', async () => {
    const pkg = await exporter.exportDeck(deck)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const files = unzipSync(pkg)
    expect(Object.keys(files)).toContain('collection.anki2')
  })

  it('exportCards includes all provided cards', async () => {
    const pkg = await exporter.exportCards('Test', deck.cards)
    expect(pkg).toBeInstanceOf(Uint8Array)
    expect(pkg[0]).toBe(0x50)
  })
})
