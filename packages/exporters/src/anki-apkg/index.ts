/**
 * AnkiApkgExporter — generates Anki .apkg files using sql.js + fflate.
 *
 * Anki .apkg = ZIP containing:
 *   collection.anki2  — SQLite database (notes, cards, col)
 *   media             — JSON mapping of media filenames (empty for text cards)
 */
import initSqlJs from 'sql.js'
import { zip, strToU8 } from 'fflate'
import type { FlashcardDeckData, Flashcard } from '@oh-my-class/renderer/contracts/flashcard_deck.js'

export interface AnkiCard {
  front: string
  back:  string
  tags?: string[]
}

// Deterministic hash-based ID from a string (avoids Date.now() non-determinism)
function stableId(seed: string): number {
  let h = 0
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(31, h) + seed.charCodeAt(i) | 0
  }
  return Math.abs(h) || 1
}

// Anki 2.1 minimal SQLite schema
const SCHEMA_SQL = `
CREATE TABLE col (
  id    INTEGER PRIMARY KEY,
  crt   INTEGER NOT NULL,
  mod   INTEGER NOT NULL,
  scm   INTEGER NOT NULL,
  ver   INTEGER NOT NULL DEFAULT 11,
  dty   INTEGER NOT NULL DEFAULT 0,
  usn   INTEGER NOT NULL DEFAULT 0,
  ls    INTEGER NOT NULL DEFAULT 0,
  conf  TEXT    NOT NULL,
  models TEXT   NOT NULL,
  decks TEXT    NOT NULL,
  dconf TEXT    NOT NULL,
  tags  TEXT    NOT NULL DEFAULT '{}'
);
CREATE TABLE notes (
  id    INTEGER PRIMARY KEY,
  guid  TEXT    NOT NULL,
  mid   INTEGER NOT NULL,
  mod   INTEGER NOT NULL,
  usn   INTEGER NOT NULL DEFAULT -1,
  tags  TEXT    NOT NULL DEFAULT '',
  flds  TEXT    NOT NULL,
  sfld  INTEGER NOT NULL,
  csum  INTEGER NOT NULL,
  flags INTEGER NOT NULL DEFAULT 0,
  data  TEXT    NOT NULL DEFAULT ''
);
CREATE TABLE cards (
  id    INTEGER PRIMARY KEY,
  nid   INTEGER NOT NULL,
  did   INTEGER NOT NULL,
  ord   INTEGER NOT NULL DEFAULT 0,
  mod   INTEGER NOT NULL,
  usn   INTEGER NOT NULL DEFAULT -1,
  type  INTEGER NOT NULL DEFAULT 0,
  queue INTEGER NOT NULL DEFAULT 0,
  due   INTEGER NOT NULL DEFAULT 0,
  ivl   INTEGER NOT NULL DEFAULT 0,
  factor INTEGER NOT NULL DEFAULT 2500,
  reps  INTEGER NOT NULL DEFAULT 0,
  lapses INTEGER NOT NULL DEFAULT 0,
  left  INTEGER NOT NULL DEFAULT 0,
  odue  INTEGER NOT NULL DEFAULT 0,
  odid  INTEGER NOT NULL DEFAULT 0,
  flags INTEGER NOT NULL DEFAULT 0,
  data  TEXT    NOT NULL DEFAULT ''
);
CREATE TABLE revlog (
  id      INTEGER PRIMARY KEY,
  cid     INTEGER NOT NULL,
  usn     INTEGER NOT NULL DEFAULT -1,
  ease    INTEGER NOT NULL,
  ivl     INTEGER NOT NULL,
  lastIvl INTEGER NOT NULL,
  factor  INTEGER NOT NULL,
  time    INTEGER NOT NULL,
  type    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE graves (
  usn  INTEGER NOT NULL,
  oid  INTEGER NOT NULL,
  type INTEGER NOT NULL
);
`

function buildColRecord(deckId: number, modelId: number, deckName: string, ts: number): string[] {
  const model = {
    [modelId]: {
      id: modelId,
      name: 'oh-my-class Basic',
      type: 0,
      mod: ts,
      usn: -1,
      sortf: 0,
      did: deckId,
      tmpls: [{
        name: 'Card 1',
        ord: 0,
        qfmt: '{{Front}}',
        afmt: '{{FrontSide}}<hr id="answer">{{Back}}',
        bqfmt: '',
        bafmt: '',
        did: null,
        bfont: '',
        bsize: 0,
      }],
      flds: [
        { name: 'Front', ord: 0, sticky: false, rtl: false, font: 'Arial', size: 20 },
        { name: 'Back',  ord: 1, sticky: false, rtl: false, font: 'Arial', size: 20 },
      ],
      css: '.card { font-family: Arial; font-size: 20px; }',
      latexPre: '',
      latexPost: '',
      tags: [],
      vers: [],
    },
  }
  const deck = {
    [deckId]: {
      id: deckId,
      name: deckName,
      desc: '',
      mod: ts,
      usn: -1,
      collapsed: false,
      browserCollapsed: false,
      newToday: [0, 0],
      revToday: [0, 0],
      lrnToday: [0, 0],
      timeToday: [0, 0],
      conf: 1,
      dyn: 0,
    },
  }
  return [JSON.stringify(model), JSON.stringify(deck)]
}

/**
 * Export a flashcard deck as an Anki .apkg file.
 *
 * @param deckName  Deck name shown in Anki browser
 * @param cards     Array of AnkiCard objects
 * @param seedTs    Stable timestamp seed for deterministic IDs (default: 1750000000)
 * @returns         Uint8Array of the .apkg ZIP
 */
export async function exportApkg(
  deckName: string,
  cards: AnkiCard[],
  seedTs = 1_750_000_000,
): Promise<Uint8Array> {
  const SQL = await initSqlJs()
  const db  = new SQL.Database()

  db.run(SCHEMA_SQL)

  const deckId  = stableId(`deck:${deckName}`)
  const modelId = stableId(`model:${deckName}`)
  const [modelsJson, decksJson] = buildColRecord(deckId, modelId, deckName, seedTs)

  db.run(
    `INSERT INTO col VALUES (?, ?, ?, ?, 11, 0, 0, 0, '{}', ?, ?, '{}', '{}')`,
    [1, seedTs, seedTs, seedTs, modelsJson, decksJson],
  )

  cards.forEach((card, i) => {
    const noteId = stableId(`note:${deckName}:${i}`)
    const cardId = stableId(`card:${deckName}:${i}`)
    const tagStr = (card.tags ?? []).join(' ')
    const flds   = `${card.front}\x1f${card.back}`

    db.run(
      `INSERT INTO notes VALUES (?, ?, ?, ?, -1, ?, ?, 0, 0, 0, '')`,
      [noteId, `guid-${noteId}`, modelId, seedTs, tagStr, flds],
    )
    db.run(
      `INSERT INTO cards VALUES (?, ?, ?, 0, ?, -1, 0, 0, ?, 0, 2500, 0, 0, 0, 0, 0, 0, '')`,
      [cardId, noteId, deckId, seedTs, i],
    )
  })

  const sqliteData = db.export()
  db.close()

  return new Promise((resolve, reject) => {
    zip(
      {
        'collection.anki2': sqliteData,
        'media':            strToU8('{}'),
      },
      (err, data) => (err ? reject(err) : resolve(data)),
    )
  })
}

export class AnkiApkgExporter {
  async exportDeck(deck: FlashcardDeckData, seedTs?: number): Promise<Uint8Array> {
    const cards: AnkiCard[] = deck.cards.map(c => ({
      front: c.front,
      back:  c.back,
      tags:  [deck.subject, deck.gradeLevel].filter(Boolean),
    }))
    return exportApkg(deck.title, cards, seedTs)
  }

  async exportCards(deckName: string, cards: Flashcard[], tags: string[] = [], seedTs?: number): Promise<Uint8Array> {
    const ankiCards: AnkiCard[] = cards.map(c => ({ front: c.front, back: c.back, tags }))
    return exportApkg(deckName, ankiCards, seedTs)
  }
}

export const ankiApkgExporter = new AnkiApkgExporter()
