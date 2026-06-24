import { describe, it, expect } from 'vitest'
import type { LessonPlan, GagneEvent, LessonPhase, DesiredResults, AssessmentEvidence } from '../../src/contracts/schemas/lesson-plan.js'
import type { CurriculumStandard } from '../../src/contracts/curriculum-standard.js'

const ALL_GAGNE_EVENTS: GagneEvent[] = [
  'gain_attention',
  'inform_objectives',
  'recall_prior',
  'present_content',
  'provide_guidance',
  'elicit_performance',
  'provide_feedback',
  'assess_performance',
  'enhance_retention',
]

function makePhase(event: GagneEvent): LessonPhase {
  return {
    event,
    title:       `Phase: ${event}`,
    duration:    5,
    description: `Description for ${event}`,
    activities:  ['Activity 1'],
  }
}

const standard: CurriculumStandard = {
  framework:   'moet_gdpt_2018',
  code:        'GDPT-ENG-10-L1',
  description: 'Listen and comprehend main ideas',
  grade:       10,
  subject:     'english',
}

const stage1: DesiredResults = {
  learningObjectives: [
    { id: 'lo1', text: 'Students will be able to summarise a text', bloomLevel: 'understand' },
  ],
  essentialQuestions:     ['Why do we read?'],
  enduringUnderstandings: ['Reading builds comprehension'],
  knowledge:  ['Vocabulary terms'],
  skills:     ['Summarising', 'Identifying main ideas'],
}

const stage2: AssessmentEvidence = {
  performanceTasks: [
    {
      goal:      'Summarise a passage',
      role:      'Student',
      audience:  'Teacher',
      situation: 'End of lesson',
      product:   'Written summary',
      standards: 'At least 3 main ideas',
    },
  ],
  otherEvidence: ['Exit ticket', 'Class discussion'],
}

const lessonPlan: LessonPlan = {
  id:         'lp-001',
  title:      'Introduction to Photosynthesis',
  subject:    'science',
  topic:      'Photosynthesis',
  gradeLevel: [6, 7],
  duration:   45,
  language:   'en',
  standards:  [standard],
  prerequisites: ['Basic cell biology'],
  stage1,
  stage2,
  stage3: { phases: ALL_GAGNE_EVENTS.map(makePhase) },
  materials:  ['Textbook', 'Worksheet'],
  vocabulary: [
    { term: 'Photosynthesis', definition: 'Process by which plants make food' },
  ],
}

describe('LessonPlan schema', () => {
  it('has required top-level fields', () => {
    expect(lessonPlan.id).toBe('lp-001')
    expect(lessonPlan.title).toBeDefined()
    expect(lessonPlan.subject).toBeDefined()
    expect(lessonPlan.gradeLevel).toBeInstanceOf(Array)
    expect(lessonPlan.duration).toBeGreaterThan(0)
  })

  it('supports all 3 language values', () => {
    const langs: LessonPlan['language'][] = ['vi', 'en', 'bilingual']
    for (const lang of langs) {
      const lp = { ...lessonPlan, language: lang }
      expect(lp.language).toBe(lang)
    }
  })

  it('stage3 has all 9 Gagné events', () => {
    const events = lessonPlan.stage3.phases.map(p => p.event)
    for (const ev of ALL_GAGNE_EVENTS) {
      expect(events).toContain(ev)
    }
  })

  it('stage1 DesiredResults has all required fields', () => {
    expect(stage1.learningObjectives).toBeInstanceOf(Array)
    expect(stage1.essentialQuestions).toBeInstanceOf(Array)
    expect(stage1.enduringUnderstandings).toBeInstanceOf(Array)
    expect(stage1.knowledge).toBeInstanceOf(Array)
    expect(stage1.skills).toBeInstanceOf(Array)
  })

  it('stage2 AssessmentEvidence has performanceTasks with GRASPS fields', () => {
    const task = stage2.performanceTasks[0]
    expect(task).toHaveProperty('goal')
    expect(task).toHaveProperty('role')
    expect(task).toHaveProperty('audience')
    expect(task).toHaveProperty('situation')
    expect(task).toHaveProperty('product')
    expect(task).toHaveProperty('standards')
  })

  it('CurriculumStandard accepts all 8 framework types', () => {
    const frameworks: CurriculumStandard['framework'][] = [
      'moet_gdpt_2018',
      'moet_decision_3439',
      'moet_circular_02_2025',
      'ccss_math',
      'ccss_ela',
      'cambridge',
      'ielts',
      'custom',
    ]
    for (const fw of frameworks) {
      const s: CurriculumStandard = { ...standard, framework: fw }
      expect(s.framework).toBe(fw)
    }
  })

  it('differentiation is optional', () => {
    const lp: LessonPlan = { ...lessonPlan, differentiation: undefined }
    expect(lp.differentiation).toBeUndefined()
  })
})
