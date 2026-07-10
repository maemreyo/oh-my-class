/**
 * Export CLI bridge (stdin → stdout).
 *
 * Invoked by the Python export adapter (teaching_pack_export_writer.py).
 * Input  (stdin, JSON):  { format, run_id, artifacts, output_dir }
 * Output (stdout, JSON): { path } on success  |  process exits 1 on failure
 *
 * Fail-closed: any error writes nothing and exits non-zero.
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import type { ExportFormat } from './index.js'
import type { BaseQuestion } from '@oh-my-class/renderer/contracts/questions/base.js'

type ArtifactEntry = { artifact_type: string; content: Record<string, unknown> }

interface CliInput {
  format: Extract<ExportFormat, 'anki_apkg' | 'flashcard_tsv' | 'gift' | 'h5p' | 'qti'>
  run_id: string
  artifacts: ArtifactEntry[]
  output_dir: string
}

interface FlashcardShape {
  id?: unknown
  front: string
  back: string
  hint?: string
}

interface QuizQuestionShape {
  id?: unknown
  prompt: string
  answer: string
}

export function extractQuestions(artifacts: ArtifactEntry[]): BaseQuestion[] {
  const questions: BaseQuestion[] = []
  for (const artifact of artifacts) {
    const sections = artifact.content.sections
    if (!Array.isArray(sections)) continue
    for (const section of sections) {
      const sec = section as Record<string, unknown>
      const qs = sec.questions
      if (!Array.isArray(qs)) continue
      for (const q of qs) {
        if (typeof q === 'object' && q !== null && 'id' in q && 'type' in q) {
          questions.push(q as BaseQuestion)
        }
      }
    }
  }
  return questions
}

async function run(): Promise<void> {
  const chunks: Buffer[] = []
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer)
  const input: CliInput = JSON.parse(Buffer.concat(chunks).toString('utf-8'))

  const { format, run_id, artifacts, output_dir } = input
  await mkdir(output_dir, { recursive: true })

  if (format === 'gift') {
    const { GIFTExporter } = await import('./gift-impl/index.js')
    const exporter = new GIFTExporter()
    const questions = extractQuestions(artifacts)
    const gift = exporter.export(questions, run_id)
    const outPath = join(output_dir, `${run_id}.gift.txt`)
    await writeFile(outPath, gift, 'utf-8')
    process.stdout.write(JSON.stringify({ path: outPath }))
    return
  }

  if (format === 'h5p') {
    const { H5PExporter } = await import('./h5p-impl/index.js')
    const exporter = new H5PExporter()
    const questions = extractQuestions(artifacts)
    let outPath = ''
    for (const q of questions) {
      const pkg = await exporter.exportQuestion(q)
      if (pkg) {
        outPath = join(output_dir, `${run_id}.h5p`)
        await writeFile(outPath, pkg)
        break
      }
    }
    if (!outPath) {
      throw new Error('No supported question type found for H5P export')
    }
    process.stdout.write(JSON.stringify({ path: outPath }))
    return
  }

  if (format === 'qti') {
    const { QTIExporter } = await import('@oh-my-class/renderer/exporters/qti/index.js')
    const exporter = new QTIExporter()
    const questions = extractQuestions(artifacts)
    const xml = exporter.export(questions)
    const outPath = join(output_dir, `${run_id}.qti.xml`)
    await writeFile(outPath, xml, 'utf-8')
    process.stdout.write(JSON.stringify({ path: outPath }))
    return
  }

  const deck = buildDeck(run_id, artifacts)

  if (format === 'anki_apkg') {
    const { AnkiApkgExporter } = await import('./anki-apkg/index.js')
    const exporter = new AnkiApkgExporter()
    const bytes = await exporter.exportDeck(deck)
    const outPath = join(output_dir, `${run_id}.apkg`)
    await writeFile(outPath, bytes)
    process.stdout.write(JSON.stringify({ path: outPath }))
    return
  }

  if (format === 'flashcard_tsv') {
    const { FlashcardTSVExporter } = await import('./flashcard-tsv/index.js')
    const exporter = new FlashcardTSVExporter()
    const tsv = exporter.exportDeck(deck)
    const outPath = join(output_dir, `${run_id}.tsv`)
    await writeFile(outPath, tsv, 'utf-8')
    process.stdout.write(JSON.stringify({ path: outPath }))
    return
  }

  throw new Error(`Unknown export format: ${format as string}`)
}

function buildDeck(run_id: string, artifacts: ArtifactEntry[]) {
  const cards: Array<{ id: string; front: string; back: string }> = []
  let subject = ''
  let gradeLevel = ''

  for (const artifact of artifacts) {
    const c = artifact.content

    if (artifact.artifact_type === 'flashcard_deck') {
      // Cards may be at top-level (direct FlashcardDeckData) or nested in sections
      // (ArtifactContent schema stores data in sections[].cards).
      let raw: unknown[]
      if (Array.isArray(c.cards)) {
        raw = c.cards as unknown[]
      } else {
        const sections = Array.isArray(c.sections) ? (c.sections as unknown[]) : []
        raw = sections.flatMap(s => {
          const sec = s as Record<string, unknown>
          return Array.isArray(sec.cards) ? (sec.cards as unknown[]) : []
        })
      }
      for (const card of raw) {
        const fc = card as FlashcardShape
        if (fc && typeof fc.front === 'string' && typeof fc.back === 'string') {
          cards.push({
            id: String(fc.id ?? `${run_id}-${cards.length}`),
            front: fc.front,
            back: fc.back,
          })
        }
      }
      if (typeof c.subject === 'string') subject = c.subject
      if (typeof c.gradeLevel === 'string') gradeLevel = c.gradeLevel
      // Also check metadata for subject/gradeLevel (ArtifactContent stores these in metadata)
      if (typeof c.metadata === 'object' && c.metadata !== null) {
        const meta = c.metadata as Record<string, unknown>
        if (!subject && typeof meta.subject === 'string') subject = meta.subject
        if (!gradeLevel && typeof meta.gradeLevel === 'string') gradeLevel = meta.gradeLevel
      }
      continue
    }

    // Fall back: treat quiz / drill Q&A pairs as front/back cards
    if (artifact.artifact_type === 'quiz' || artifact.artifact_type === 'drill') {
      const raw = Array.isArray(c.questions) ? (c.questions as unknown[]) : []
      for (const q of raw) {
        const qq = q as QuizQuestionShape
        if (qq && typeof qq.prompt === 'string' && typeof qq.answer === 'string') {
          cards.push({
            id: String(qq.id ?? `${run_id}-${cards.length}`),
            front: qq.prompt,
            back: qq.answer,
          })
        }
      }
    }
  }

  return {
    title: `oh-my-class ${run_id}`,
    subject: subject || 'general',
    gradeLevel: gradeLevel || 'N/A',
    cards,
  }
}

run().catch(err => {
  process.stderr.write(`Export CLI error: ${String(err)}\n`)
  process.exit(1)
})
