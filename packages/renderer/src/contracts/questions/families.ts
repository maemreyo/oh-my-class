export type RenderingFamily =
  | 'choice'
  | 'text-entry'
  | 'fill-gap'
  | 'match'
  | 'order'
  | 'open'
  | 'interactive'
  | 'multimedia'

export const RENDERING_FAMILIES: readonly RenderingFamily[] = [
  'choice',
  'text-entry',
  'fill-gap',
  'match',
  'order',
  'open',
  'interactive',
  'multimedia',
]

// Single source of truth: question type → rendering family
export const FAMILY_MAP: Record<string, RenderingFamily> = {
  // ── choice ──────────────────────────────────────────────────────────────
  multiple_choice_single:   'choice',
  multiple_choice_multiple: 'choice',
  true_false_4item:         'choice',
  phonics:                  'choice',

  // ── text-entry ───────────────────────────────────────────────────────────
  cloze:                'text-entry',
  short_answer:         'text-entry',
  grammar_transformation: 'text-entry',
  reported_speech:      'text-entry',
  passive_voice:        'text-entry',
  conditional_builder:  'text-entry',
  error_correction:     'text-entry',
  sentence_manipulation: 'text-entry',

  // ── fill-gap ─────────────────────────────────────────────────────────────
  fill_blank_wordbank: 'fill-gap',
  cloze_mixed:         'fill-gap',
  dialogue_completion: 'fill-gap',

  // ── match ────────────────────────────────────────────────────────────────
  matching:            'match',
  matching_vocabulary: 'match',
  collocation:         'match',
  idioms:              'match',
  word_analysis:       'match',

  // ── order ────────────────────────────────────────────────────────────────
  ordering:             'order',
  tense_timeline:       'order',
  vocabulary_scaffolded: 'order',

  // ── open ─────────────────────────────────────────────────────────────────
  essay:       'open',
  paraphrase:  'open',
  translation: 'open',
  lab_report:  'open',
  drawing:     'open',
  performance: 'open',
  dictation:   'open',

  // ── interactive ───────────────────────────────────────────────────────────
  drag_and_drop:       'interactive',
  branching_scenario:  'interactive',
  step_by_step_math:   'interactive',
  geometric_proof:     'interactive',
  data_interpretation: 'interactive',
  coding_exercise:     'interactive',
  financial_literacy:  'interactive',
  measurement:         'interactive',

  // ── multimedia ────────────────────────────────────────────────────────────
  multimedia_video:         'multimedia',
  multimedia_audio:         'multimedia',
  multimedia_photo:         'multimedia',
  experiment_documentation: 'multimedia',
  parent_child_activity:    'multimedia',
  field_trip_journal:       'multimedia',
  art_project:              'multimedia',
}
