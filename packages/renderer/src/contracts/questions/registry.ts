import type { ArtifactType } from '../index.js'
import type { BloomLevel, MOETLevel, Subject, ExamFormat } from './base.js'
import type { RenderingFamily } from './families.js'
import { FAMILY_MAP } from './families.js'

export interface QuestionTypeMeta {
  type:           string
  family:         RenderingFamily
  label:          string
  labelVi:        string
  artifacts:      ArtifactType[]
  bloomLevels:    BloomLevel[]
  moetLevels?:    MOETLevel[]
  subjects:       Subject[]
  examFormats:    ExamFormat[]
  requiresMedia:  boolean
  isInteractive:  boolean
  complexity:     'low' | 'medium' | 'high'
  qtiInteraction: string
}

export interface QueryCriteria {
  artifactType?:  ArtifactType
  bloomLevel?:    BloomLevel
  moetLevel?:     MOETLevel
  subject?:       Subject
  examFormat?:    ExamFormat
  requiresMedia?: boolean
  isInteractive?: boolean
  maxComplexity?: 'low' | 'medium' | 'high'
}

const COMPLEXITY_ORDER: Record<'low' | 'medium' | 'high', number> = {
  low: 0, medium: 1, high: 2,
}

export class QuestionTypeRegistry {
  private _types = new Map<string, QuestionTypeMeta>()

  register(meta: QuestionTypeMeta): void {
    if (!(meta.type in FAMILY_MAP)) {
      throw new Error(`register: type "${meta.type}" has no entry in FAMILY_MAP`)
    }
    this._types.set(meta.type, meta)
  }

  query(criteria: QueryCriteria): QuestionTypeMeta[] {
    return [...this._types.values()].filter(m => {
      if (criteria.artifactType !== undefined &&
          !m.artifacts.includes(criteria.artifactType)) return false
      if (criteria.bloomLevel !== undefined &&
          !m.bloomLevels.includes(criteria.bloomLevel)) return false
      if (criteria.moetLevel !== undefined &&
          !(m.moetLevels?.includes(criteria.moetLevel))) return false
      if (criteria.subject !== undefined &&
          !m.subjects.includes(criteria.subject) &&
          !m.subjects.includes('all')) return false
      if (criteria.examFormat !== undefined &&
          !m.examFormats.includes(criteria.examFormat)) return false
      if (criteria.requiresMedia !== undefined &&
          m.requiresMedia !== criteria.requiresMedia) return false
      if (criteria.isInteractive !== undefined &&
          m.isInteractive !== criteria.isInteractive) return false
      if (criteria.maxComplexity !== undefined &&
          COMPLEXITY_ORDER[m.complexity] > COMPLEXITY_ORDER[criteria.maxComplexity]) return false
      return true
    })
  }

  getFamily(type: string): RenderingFamily {
    const meta = this._types.get(type)
    if (!meta) throw new Error(`getFamily: unknown question type "${type}"`)
    return meta.family
  }

  supports(type: string, artifact: ArtifactType): boolean {
    return this._types.get(type)?.artifacts.includes(artifact) ?? false
  }

  get(type: string): QuestionTypeMeta | undefined {
    return this._types.get(type)
  }

  all(): QuestionTypeMeta[] {
    return [...this._types.values()]
  }

  size(): number {
    return this._types.size
  }
}

// Singleton — populated by registering all types at module init
export const questionRegistry = new QuestionTypeRegistry()
