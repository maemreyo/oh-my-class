import type { BatchUpdateRequest } from './google-forms/client.js'

export type InverseThinkingExportFormat = 'html' | 'gift' | 'h5p' | 'qti' | 'google_forms'
export type InverseThinkingSupportLevel = 'supported' | 'unsupported' | 'lossy'

export interface InverseThinkingTeacherOnly {
  readonly rationale: string
  readonly answer_key: string
}

export interface InverseThinkingCase {
  readonly id: string
  readonly title: string
  readonly target_concept: string
  readonly foil: string
  readonly disaster: string
  readonly key_clues: readonly string[]
  readonly safe_zone: string
  readonly filing_note: string
  readonly student_task: string
  readonly teacher_only: InverseThinkingTeacherOnly
}

export interface InverseThinkingPack {
  readonly methodology: 'inverse_thinking'
  readonly cases: readonly InverseThinkingCase[]
  readonly teacher_only: InverseThinkingTeacherOnly
}

export interface InverseThinkingFormatSupport {
  readonly format: InverseThinkingExportFormat
  readonly level: InverseThinkingSupportLevel
  readonly preserves: readonly string[]
  readonly warnings: readonly string[]
}

export interface GoogleFormsMappingResult {
  readonly requests: readonly BatchUpdateRequest[]
  readonly warnings: readonly string[]
}

export class UnsupportedInverseThinkingExportError extends Error {
  readonly format: InverseThinkingExportFormat
  readonly remediation: string

  constructor(format: InverseThinkingExportFormat, remediation: string) {
    super(`Inverse-thinking export to ${format} cannot preserve required semantics. ${remediation}`)
    this.name = 'UnsupportedInverseThinkingExportError'
    this.format = format
    this.remediation = remediation
  }
}

export const INVERSE_THINKING_FORMAT_SUPPORT: readonly InverseThinkingFormatSupport[] = [
  { format: 'html', level: 'supported', preserves: ['case_title', 'disaster', 'key_clues', 'safe_zone', 'teacher_rationale'], warnings: [] },
  { format: 'gift', level: 'supported', preserves: ['case_title', 'disaster', 'misconception_choices', 'correct_answer', 'teacher_rationale'], warnings: [] },
  { format: 'h5p', level: 'unsupported', preserves: [], warnings: ['No bundled H5P content type preserves disaster-first flow plus safe-zone feedback.'] },
  { format: 'qti', level: 'supported', preserves: ['case_id', 'disaster', 'choices', 'correct_answer', 'feedback'], warnings: [] },
  { format: 'google_forms', level: 'lossy', preserves: ['case_title', 'disaster', 'correct_answer'], warnings: ['Safe-zone feedback and partial-credit semantics are degraded.'] },
]

export function supportForInverseThinking(format: InverseThinkingExportFormat): InverseThinkingFormatSupport {
  const support = INVERSE_THINKING_FORMAT_SUPPORT.find((entry) => entry.format === format)
  if (!support) {
    throw new UnsupportedInverseThinkingExportError(format, 'Request html, gift, or qti instead.')
  }
  return support
}

export function exportInverseThinkingGift(pack: InverseThinkingPack): string {
  const lines = ['$CATEGORY: oh-my-class/inverse-thinking', '']
  for (const item of pack.cases) {
    lines.push(`// case_id: ${escapeGift(item.id)}`)
    lines.push(`// teacher_rationale: ${escapeGift(item.teacher_only.rationale)}`)
    lines.push(`::${escapeGift(item.id)}::[html]${escapeGift(item.title)}<br>${escapeGift(item.disaster)}{`)
    lines.push(`  =${escapeGift(item.safe_zone)}#${escapeGift(item.teacher_only.rationale)}`)
    lines.push(`  ~${escapeGift(item.foil)}`)
    for (const clue of item.key_clues) {
      lines.push(`  ~${escapeGift(clue)}`)
    }
    lines.push('}')
    lines.push('')
  }
  return lines.join('\n')
}

export async function exportInverseThinkingH5P(pack: InverseThinkingPack): Promise<Uint8Array> {
  throw new UnsupportedInverseThinkingExportError('h5p', `Use HTML, GIFT, or QTI for ${pack.cases.length} inverse-thinking case(s).`)
}

export function exportInverseThinkingQTI(pack: InverseThinkingPack): string {
  const items = pack.cases.map(qtiItem).join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>
<assessmentTest xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1" identifier="inverse-thinking" title="oh-my-class Inverse Thinking">
  <testPart identifier="part1" navigationMode="linear" submissionMode="individual">
    <assessmentSection identifier="section1" title="Inverse Thinking" visible="true">
${items}
    </assessmentSection>
  </testPart>
</assessmentTest>`
}

export function buildInverseThinkingGoogleFormsRequests(pack: InverseThinkingPack): GoogleFormsMappingResult {
  const warnings = [...supportForInverseThinking('google_forms').warnings]
  return {
    warnings,
    requests: pack.cases.map((item, index) => ({
      createItem: {
        location: { index },
        item: {
          title: `${item.title}: ${item.disaster}`,
          questionItem: {
            question: {
              required: true,
              grading: {
                pointValue: 1,
                correctAnswers: { answers: [{ value: item.safe_zone }] },
                whenRight: { text: item.teacher_only.rationale },
                whenWrong: { text: 'Review the safe-zone boundary before trying again.' },
              },
              choiceQuestion: {
                type: 'RADIO',
                options: [
                  { value: item.safe_zone },
                  { value: item.foil },
                  ...item.key_clues.map((clue) => ({ value: clue })),
                ],
                shuffle: true,
              },
            },
          },
        },
      },
    })),
  }
}

function qtiItem(item: InverseThinkingCase): string {
  const choices = [item.safe_zone, item.foil, ...item.key_clues]
  return `      <assessmentItem identifier="${escapeXml(item.id)}" title="${escapeXml(item.title)}" adaptive="false" timeDependent="false">
        <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
          <correctResponse><value>A</value></correctResponse>
        </responseDeclaration>
        <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float"><defaultValue><value>0</value></defaultValue></outcomeDeclaration>
        <itemBody><p>${escapeXml(item.disaster)}</p><choiceInteraction responseIdentifier="RESPONSE" maxChoices="1">${choices.map((choice, index) => `<simpleChoice identifier="${String.fromCharCode(65 + index)}">${escapeXml(choice)}</simpleChoice>`).join('')}</choiceInteraction></itemBody>
        <modalFeedback outcomeIdentifier="FEEDBACK" identifier="safe-zone" showHide="show">${escapeXml(item.safe_zone)}</modalFeedback>
        <modalFeedback outcomeIdentifier="FEEDBACK" identifier="rationale" showHide="show">${escapeXml(item.teacher_only.rationale)}</modalFeedback>
      </assessmentItem>`
}

function escapeGift(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/~/g, '\\~').replace(/=/g, '\\=').replace(/\{/g, '\\{').replace(/\}/g, '\\}').replace(/#/g, '\\#')
}

function escapeXml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;')
}
