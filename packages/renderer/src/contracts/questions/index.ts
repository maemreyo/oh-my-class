// Base types
export type {
  BloomLevel,
  MOETLevel,
  Subject,
  ExamFormat,
  ScoringType,
  ScoringConfig,
  RubricLevel,
  RubricCriterion,
  Rubric,
  QuestionMetadata,
  BaseQuestion,
} from './base.js'

// Rendering families
export type { RenderingFamily } from './families.js'
export { FAMILY_MAP, RENDERING_FAMILIES } from './families.js'

// Registry
export type { QuestionTypeMeta, QueryCriteria } from './registry.js'
export { QuestionTypeRegistry, questionRegistry } from './registry.js'

// Question types — choice family
export type {
  MCOption,
  MultipleChoiceSingle,
  MultipleChoiceMultiple,
  TFItem,
  TrueFalse4Item,
  PhonicsItem,
  Phonics,
  ChoiceQuestion,
} from './types/choice.js'

// Question types — text-entry family
export type {
  Cloze,
  ShortAnswer,
  GrammarTransformation,
  ReportedSpeech,
  PassiveVoice,
  ConditionalActivity,
  ConditionalBuilder,
  ErrorCorrection,
  SentenceManipulation,
  TextEntryQuestion,
} from './types/text-entry.js'

// Question types — fill-gap family
export type {
  FillBlankWordBank,
  ClozeMixed,
  DialogueTurn,
  DialogueBlank,
  DialogueCompletion,
  FillGapQuestion,
} from './types/fill-gap.js'

// Question types — match family
export type {
  MatchColumn,
  MatchPair,
  Matching,
  MatchingVocabulary,
  CollocationPair,
  Collocation,
  IdiomEntry,
  Idioms,
  Morpheme,
  WordAnalysis,
  MatchQuestion,
} from './types/match.js'

// Question types — order family
export type {
  OrderItem,
  Ordering,
  TimelineEvent,
  TenseTimelineQuestion,
  TenseTimeline,
  VocabStage,
  VocabStageEntry,
  VocabularyScaffolded,
  OrderQuestion,
} from './types/order.js'

// Question types — open family
export type {
  Essay,
  Paraphrase,
  Translation,
  LabReportSection,
  LabReport,
  Drawing,
  Performance,
  Dictation,
  OpenQuestion,
} from './types/open.js'

// Question types — interactive family
export type {
  DragZone,
  Draggable,
  DragAndDrop,
  BranchingChoice,
  BranchingNode,
  BranchingScenario,
  CGIType,
  StepType,
  MathStep,
  StepByStepMath,
  ProofStep,
  GeometricProof,
  ChartType,
  DataInterpretation,
  CodingExercise,
  FinancialLiteracy,
  MeasurementSubtype,
  Measurement,
  InteractiveQuestion,
} from './types/interactive.js'

// Question types — multimedia family
export type {
  SubmissionPlatform,
  SubmissionInfo,
  MultimediaVideo,
  MultimediaAudio,
  MultimediaPhoto,
  ExperimentDocumentation,
  ParentChildActivity,
  FieldTripSection,
  FieldTripJournal,
  ArtProject,
  MultimediaQuestion,
} from './types/multimedia.js'

// Auto-register all types at module init
import './register.js'
