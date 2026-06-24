import type { BaseQuestion } from '../base.js'

export interface DragZone {
  id:    string
  label: string
}

export interface Draggable {
  id:           string
  text:         string
  correctZone:  string
  isDistractor?: boolean
}

export interface DragAndDrop extends BaseQuestion {
  type:         'drag_and_drop'
  instructions: string
  zones:        DragZone[]
  draggables:   Draggable[]
}

export interface BranchingChoice {
  text:       string
  nextNode:   string
  xpReward?:  number
}

export interface BranchingNode {
  id:        string
  prompt:    string
  choices:   BranchingChoice[]
  question?: Record<string, unknown>
}

export interface BranchingScenario extends BaseQuestion {
  type:          'branching_scenario'
  title:         string
  initialPrompt: string
  nodes:         BranchingNode[]
  outcomes:      Record<string, string>
}

export type CGIType =
  | 'join_result_unknown'
  | 'join_change_unknown'
  | 'join_start_unknown'
  | 'separate_result_unknown'
  | 'separate_change_unknown'
  | 'separate_start_unknown'
  | 'part_part_whole_total_unknown'
  | 'part_part_whole_part_unknown'
  | 'compare_difference_unknown'
  | 'compare_referent_unknown'

export type StepType = 'fill_blank' | 'multiple_choice_single' | 'fill_blank_free' | 'true_false'

export interface MathStep {
  order:         number
  instruction:   string
  type:          StepType
  correctAnswer: string | boolean
  options?:      Array<{ id: string; text: string; isCorrect: boolean }>
}

export interface StepByStepMath extends BaseQuestion {
  type:    'step_by_step_math'
  cgiType: CGIType
  problem: string
  steps:   MathStep[]
}

export interface ProofStep {
  statement:      string
  reason:         string
  type:           'given' | 'inference' | 'blank'
  correctReason?: string
}

export interface GeometricProof extends BaseQuestion {
  type:    'geometric_proof'
  diagram: { type: string; givens: string[] }
  prove:   string
  format:  'two_column' | 'paragraph'
  steps:   ProofStep[]
}

export type ChartType = 'line_graph' | 'bar_chart' | 'pie_chart' | 'scatter_plot' | 'table'

export interface DataInterpretation extends BaseQuestion {
  type:        'data_interpretation'
  dataDisplay: {
    type:   ChartType
    title:  string
    xAxis?: string
    yAxis?: string
    data:   Array<Record<string, unknown>>
  }
  questions: Array<Record<string, unknown>>
}

export interface CodingExercise extends BaseQuestion {
  type:          'coding_exercise'
  subtype:       'trace_output' | 'bug_find' | 'write_code' | 'pseudo_code'
  language?:     string
  codeBlock:     string
  question:      string
  correctAnswer: string
}

export interface FinancialLiteracy extends BaseQuestion {
  type:      'financial_literacy'
  scenario:  string
  questions: Array<{
    type:          string
    stem:          string
    correctAnswer: string
    tolerance?:    number
  }>
}

export type MeasurementSubtype = 'tool_reading' | 'unit_conversion' | 'estimation'

export interface Measurement extends BaseQuestion {
  type:    'measurement'
  subtype: MeasurementSubtype
  tool?: {
    type:     string
    readings: Array<{ value: number; unit: string; tolerance: number }>
  }
  questions: Array<{ stem: string; correctAnswer: string; tolerance?: number }>
}

export type InteractiveQuestion =
  | DragAndDrop
  | BranchingScenario
  | StepByStepMath
  | GeometricProof
  | DataInterpretation
  | CodingExercise
  | FinancialLiteracy
  | Measurement
