import { describe, it, expect } from 'vitest'
import { unzipSync, strFromU8 } from 'fflate'
import { H5PExporter } from '../src/h5p-impl/index.js'
import { buildH5PPackage } from '../src/h5p-impl/packager.js'
import type { MultipleChoiceSingle, TrueFalse4Item } from '@oh-my-class/renderer/contracts/questions/types/choice.js'
import type { Cloze } from '@oh-my-class/renderer/contracts/questions/types/text-entry.js'
import type { ClozeMixed, FillBlankWordBank } from '@oh-my-class/renderer/contracts/questions/types/fill-gap.js'
import type { FlashcardDeckData } from '@oh-my-class/renderer/contracts/flashcard_deck.js'
import type { RecapData } from '@oh-my-class/renderer/contracts/recap.js'

function readZip(pkg: Uint8Array): { h5pJson: Record<string, unknown>; contentJson: unknown } {
  const files = unzipSync(pkg)
  const h5pJson = JSON.parse(strFromU8(files['h5p.json']!))
  const contentJson = JSON.parse(strFromU8(files['content/content.json']!))
  return { h5pJson, contentJson }
}

const baseMeta = {
  difficulty: 'remember' as const,
  tags: [],
  metadata: { subject: 'english' as const, grade: 8, topic: 'vocab' },
}

const mcSingle: MultipleChoiceSingle = {
  ...baseMeta,
  id:   'mc-h5p-001',
  type: 'multiple_choice_single',
  stem: 'What colour is the sky?',
  options: [
    { id: 'A', text: 'Red',  isCorrect: false },
    { id: 'B', text: 'Blue', isCorrect: true  },
    { id: 'C', text: 'Green',isCorrect: false },
  ],
}

const tf4: TrueFalse4Item = {
  ...baseMeta,
  id:   'tf-h5p-001',
  type: 'true_false_4item',
  stem: 'True or False?',
  items: [
    { id: 'a', text: 'Cats are mammals', isTrue: true  },
    { id: 'b', text: 'Fish can fly',     isTrue: false },
    { id: 'c', text: 'Dogs bark',        isTrue: true  },
    { id: 'd', text: 'Fish breathe air', isTrue: false },
  ],
}

const clozeBasic: Cloze = {
  ...baseMeta,
  id: 'cloze-h5p-001',
  type: 'cloze',
  clozeType: 'grammar',
  passage: 'She ___ to school every day.',
  blanks: [{ id: 1, correctAnswer: 'goes' }],
  caseSensitive: false,
}

const clozeMixed: ClozeMixed = {
  ...baseMeta,
  id: 'cloze-mixed-h5p-001',
  type: 'cloze_mixed',
  clozeSubtype: 'grammar',
  passage: 'They ___ English and ___ math.',
  blanks: [
    { id: 1, correctAnswer: 'study', type: 'grammar' },
    { id: 2, correctAnswer: 'practice', type: 'vocabulary' },
  ],
}

const fillBlank: FillBlankWordBank = {
  ...baseMeta,
  id: 'fill-blank-h5p-001',
  type: 'fill_blank_wordbank',
  context: 'The cat sat on the ___.',
  blanks: [{ id: 1, correctAnswer: 'mat' }],
  wordBank: ['mat', 'hat', 'bat'],
  distractors: ['hat', 'bat'],
  shuffleWordBank: true,
}

const deck: FlashcardDeckData = {
  title:      'Science Vocab',
  subject:    'science',
  gradeLevel: '7',
  cards: [
    { id: 'c1', front: 'Photosynthesis', back: 'Process plants use to make food' },
  ],
}

const exporter = new H5PExporter()

describe('buildH5PPackage', () => {
  it('returns a non-empty Uint8Array (ZIP magic bytes PK)', async () => {
    const pkg = await buildH5PPackage({
      title: 'Test',
      mainLibrary: 'H5P.MultiChoice',
      content: { question: 'hello', answers: [] },
    })
    expect(pkg).toBeInstanceOf(Uint8Array)
    // ZIP files start with PK (0x50 0x4B)
    expect(pkg[0]).toBe(0x50)
    expect(pkg[1]).toBe(0x4B)
  })

  it('h5p.json contains mainLibrary field', async () => {
    const pkg = await buildH5PPackage({
      title: 'Test H5P',
      mainLibrary: 'H5P.TrueFalse',
      content: { correct: true, question: 'test' },
    })
    const { h5pJson } = readZip(pkg)
    expect(h5pJson.mainLibrary).toBe('H5P.TrueFalse')
    expect(h5pJson.title).toBe('Test H5P')
  })

  it('content/content.json contains the passed content object', async () => {
    const pkg = await buildH5PPackage({
      title: 'Test',
      mainLibrary: 'H5P.MultiChoice',
      content: { myKey: 'myValue' },
    })
    const { contentJson } = readZip(pkg)
    expect((contentJson as any).myKey).toBe('myValue')
  })
})

describe('H5PExporter', () => {
  it('exports multiple_choice_single as H5P.MultiChoice ZIP', async () => {
    const pkg = await exporter.exportQuestion(mcSingle)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const { h5pJson } = readZip(pkg!)
    expect(h5pJson.mainLibrary).toBe('H5P.MultiChoice')
  })

  it('exports true_false_4item (first item) as H5P.TrueFalse ZIP', async () => {
    const pkg = await exporter.exportQuestion(tf4)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const { h5pJson } = readZip(pkg!)
    expect(h5pJson.mainLibrary).toBe('H5P.TrueFalse')
  })

  it('exports cloze as H5P.Blanks ZIP', async () => {
    const pkg = await exporter.exportQuestion(clozeBasic)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const { h5pJson, contentJson } = readZip(pkg!)
    expect(h5pJson.mainLibrary).toBe('H5P.Blanks')
    expect((contentJson as { text?: string }).text).toBe('<p>She *goes* to school every day.</p>')
  })

  it('exports cloze_mixed as H5P.Blanks ZIP', async () => {
    const pkg = await exporter.exportQuestion(clozeMixed)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const { h5pJson, contentJson } = readZip(pkg!)
    expect(h5pJson.mainLibrary).toBe('H5P.Blanks')
    expect((contentJson as { text?: string }).text).toBe('<p>They *study* English and *practice* math.</p>')
  })

  it('exports fill_blank_wordbank as H5P.Blanks ZIP', async () => {
    const pkg = await exporter.exportQuestion(fillBlank)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const { h5pJson, contentJson } = readZip(pkg!)
    expect(h5pJson.mainLibrary).toBe('H5P.Blanks')
    expect((contentJson as { text?: string }).text).toBe('<p>The cat sat on the *mat*.</p>')
  })

  it('returns null for unsupported question types', async () => {
    const unknown = { ...baseMeta, id: 'x', type: 'essay' } as any
    const pkg = await exporter.exportQuestion(unknown)
    expect(pkg).toBeNull()
  })

  it('exports flashcard deck as H5P.Flashcards ZIP', async () => {
    const pkg = await exporter.exportFlashcards(deck)
    expect(pkg).toBeInstanceOf(Uint8Array)
    const { h5pJson } = readZip(pkg)
    expect(h5pJson.mainLibrary).toBe('H5P.Flashcards')
  })
})
