import { describe, it, expect } from 'vitest'
import { extractQuestions } from '../src/cli.js'
import { GIFTExporter } from '../src/gift-impl/index.js'
import { H5PExporter } from '../src/h5p-impl/index.js'
import { UnsupportedFormatError } from '../src/qti/qti.js'
import type { BaseQuestion } from '@oh-my-class/renderer/contracts/questions/base.js'

type ArtifactEntry = { artifact_type: string; content: Record<string, unknown> }

const mcqQuestion: BaseQuestion = {
  id: 'q1',
  type: 'multiple_choice_single',
  stem: 'What is 2 + 2?',
  options: [
    { id: 'a', text: '3', isCorrect: false },
    { id: 'b', text: '4', isCorrect: true },
    { id: 'c', text: '5', isCorrect: false },
    { id: 'd', text: '6', isCorrect: false },
  ],
  difficulty: 'remember',
  metadata: { subject: 'math', grade: 3, topic: 'addition' },
  tags: [],
}

const shortAnswerQuestion: BaseQuestion = {
  id: 'q2',
  type: 'short_answer',
  stem: 'What is the capital of Vietnam?',
  correctAnswer: 'Hanoi',
  acceptableAnswers: ['Ha Noi'],
  difficulty: 'remember',
  metadata: { subject: 'geography', grade: 5, topic: 'capitals' },
  tags: [],
}

function makeArtifact(questions: BaseQuestion[]): ArtifactEntry {
  return {
    artifact_type: 'quiz',
    content: {
      title: 'Test Quiz',
      sections: [{ id: 's1', questions }],
    },
  }
}

describe('extractQuestions', () => {
  it('extracts questions from artifact sections', () => {
    const artifacts = makeArtifact([mcqQuestion, shortAnswerQuestion])
    const questions = extractQuestions([artifacts])
    expect(questions).toHaveLength(2)
    expect(questions[0]!.id).toBe('q1')
    expect(questions[1]!.id).toBe('q2')
  })

  it('returns empty array when no sections exist', () => {
    const artifacts: ArtifactEntry[] = [{ artifact_type: 'lesson', content: { title: 'Intro' } }]
    expect(extractQuestions(artifacts)).toHaveLength(0)
  })

  it('returns empty array when sections have no questions', () => {
    const artifacts: ArtifactEntry[] = [{
      artifact_type: 'lesson',
      content: { sections: [{ id: 's1', title: 'Intro' }] },
    }]
    expect(extractQuestions(artifacts)).toHaveLength(0)
  })

  it('skips objects without id and type fields', () => {
    const artifacts: ArtifactEntry[] = [{
      artifact_type: 'quiz',
      content: { sections: [{ id: 's1', questions: [{ foo: 'bar' }, mcqQuestion] }] },
    }]
    const questions = extractQuestions(artifacts)
    expect(questions).toHaveLength(1)
    expect(questions[0]!.id).toBe('q1')
  })

  it('collects questions from multiple artifacts', () => {
    const a1 = makeArtifact([mcqQuestion])
    const a2 = makeArtifact([shortAnswerQuestion])
    const questions = extractQuestions([a1, a2])
    expect(questions).toHaveLength(2)
  })
})

describe('gift format via GIFTExporter', () => {
  it('exports MCQ questions to valid GIFT text', () => {
    const exporter = new GIFTExporter()
    const gift = exporter.export([mcqQuestion], 'test_category')
    expect(gift).toContain('$CATEGORY: test_category')
    expect(gift).toContain('What is 2 + 2?')
    expect(gift).toContain('=4')
    expect(gift).toContain('~3')
  })

  it('exports short answer questions to valid GIFT text', () => {
    const exporter = new GIFTExporter()
    const gift = exporter.export([shortAnswerQuestion], 'geo')
    expect(gift).toContain('=Hanoi')
    expect(gift).toContain('Ha Noi')
  })
})

describe('h5p format via H5PExporter', () => {
  it('exports MCQ question to a valid H5P ZIP', async () => {
    const exporter = new H5PExporter()
    const pkg = await exporter.exportQuestion(mcqQuestion)
    expect(pkg).toBeInstanceOf(Uint8Array)
    expect(pkg![0]).toBe(0x50)
    expect(pkg![1]).toBe(0x4B)
  })

  it('returns null for unsupported question types', async () => {
    const unsupported: BaseQuestion = {
      ...mcqQuestion,
      type: 'drawing',
    }
    const exporter = new H5PExporter()
    const pkg = await exporter.exportQuestion(unsupported)
    expect(pkg).toBeNull()
  })
})

describe('qti format throws UnsupportedFormatError', () => {
  it('qti is not yet implemented', async () => {
    await expect(
      import('../src/qti/qti.js').then(m => m.generateQTI([])),
    ).rejects.toThrow(UnsupportedFormatError)
  })
})
