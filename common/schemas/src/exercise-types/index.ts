// Base
export {
  BaseQuestionSchema,
  ScoringConfigSchema,
  RubricSchema,
  RubricCriterionSchema,
  DifficultySchema,
  BloomLevelVNSchema,
  MetadataSchema,
} from "./base.js";
export type {
  BaseQuestion,
  ScoringConfig,
  Rubric,
  Difficulty,
  BloomLevelVN,
} from "./base.js";

// Core Assessment
export {
  MultipleChoiceSingleSchema,
  MultipleChoiceMultipleSchema,
  MultipleChoiceOptionSchema,
  TrueFalse4ItemSchema,
  TFFourItemSchema,
  VietnameseTFScoringSchema,
  ShortAnswerSchema,
  EssaySchema,
  FillBlankWordBankSchema,
  ClozeSchema,
  MatchingSchema,
  OrderingSchema,
  DragAndDropSchema,
  DrawingSchema,
  PerformanceSchema,
} from "./core.js";

// English
export {
  VocabularyScaffoldedSchema,
  ClozeMixedSchema,
  MatchingVocabularySchema,
  ReadingComprehensionSchema,
  GrammarTransformationSchema,
  ErrorCorrectionSchema,
  SentenceManipulationSchema,
  ParaphraseSchema,
  DialogueCompletionSchema,
  PhonicsSchema,
  DictationSchema,
  TranslationSchema,
  IdiomsSchema,
  CollocationSchema,
  WordAnalysisSchema,
  TenseTimelineSchema,
  ConditionalBuilderSchema,
  ReportedSpeechSchema,
  PassiveVoiceSchema,
} from "./english.js";

// Math/Science
export {
  StepByStepMathSchema,
  GeometricProofSchema,
  DataInterpretationSchema,
  LabReportSchema,
  MeasurementSchema,
  CodingExerciseSchema,
  FinancialLiteracySchema,
} from "./math-science.js";

// Multimedia
export {
  MultimediaVideoSchema,
  MultimediaAudioSchema,
  MultimediaPhotoSchema,
  ExperimentDocumentationSchema,
  ParentChildActivitySchema,
  FieldTripJournalSchema,
  ArtProjectSchema,
} from "./multimedia.js";

// Gamified
export {
  TimedChallengeSchema,
  StreakSystemSchema,
  AdaptiveDifficultySchema,
  BranchingScenarioSchema,
  BranchingScenarioNodeSchema,
  CollaborativeActivitySchema,
} from "./gamified.js";
