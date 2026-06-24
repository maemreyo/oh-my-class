import type { BaseQuestion } from '../../contracts/questions/base.js'
import type { IQTISerializer } from './types.js'
import type { RenderingFamily } from '../../contracts/questions/families.js'
import { FAMILY_MAP } from '../../contracts/questions/families.js'
import { choiceSerializer } from './serializers/choice.js'
import { textEntrySerializer } from './serializers/text-entry.js'
import { fillGapSerializer } from './serializers/fill-gap.js'
import { matchSerializer } from './serializers/match.js'
import { orderSerializer } from './serializers/order.js'
import { openSerializer } from './serializers/open.js'
import { interactiveSerializer } from './serializers/interactive.js'
import { multimediaSerializer } from './serializers/multimedia.js'

export type { IQTISerializer } from './types.js'

const SERIALIZERS: Record<RenderingFamily, IQTISerializer> = {
  'choice':      choiceSerializer as IQTISerializer,
  'text-entry':  textEntrySerializer as IQTISerializer,
  'fill-gap':    fillGapSerializer as IQTISerializer,
  'match':       matchSerializer as IQTISerializer,
  'order':       orderSerializer as IQTISerializer,
  'open':        openSerializer as IQTISerializer,
  'interactive': interactiveSerializer as IQTISerializer,
  'multimedia':  multimediaSerializer as IQTISerializer,
}

export class QTIExporter {
  // Returns a QTI v3.0 assessmentTest XML wrapping all items
  export(questions: BaseQuestion[]): string {
    const items = questions.map(q => {
      const family = FAMILY_MAP[q.type]
      if (!family) throw new Error(`QTIExporter: unknown question type "${q.type}"`)
      return SERIALIZERS[family].serialize(q)
    })

    return [
      `<?xml version="1.0" encoding="UTF-8"?>`,
      `<assessmentTest xmlns="http://www.imsglobal.org/xsd/imsqti_v3p0"`,
      `  identifier="test-${Date.now()}"`,
      `  title="oh-my-class Export">`,
      `  <testPart identifier="part1" navigationMode="linear" submissionMode="individual">`,
      `    <assessmentSection identifier="section1" title="Questions" visible="true">`,
      ...items.map(xml => `      <!-- item -->\n${xml}`),
      `    </assessmentSection>`,
      `  </testPart>`,
      `</assessmentTest>`,
    ].join('\n')
  }

  // Returns a single assessmentItem XML for one question
  exportOne(question: BaseQuestion): string {
    const family = FAMILY_MAP[question.type]
    if (!family) throw new Error(`QTIExporter: unknown question type "${question.type}"`)
    return SERIALIZERS[family].serialize(question)
  }
}

export const qtiExporter = new QTIExporter()
