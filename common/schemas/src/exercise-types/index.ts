// Base

export type {
	BaseQuestion,
	BloomLevelVN,
	Difficulty,
	Rubric,
	ScoringConfig,
} from "./base.js";
export {
	BaseQuestionSchema,
	BloomLevelVNSchema,
	DifficultySchema,
	MetadataSchema,
	RubricCriterionSchema,
	RubricSchema,
	ScoringConfigSchema,
} from "./base.js";

// Core Assessment
export {
	ClozeSchema,
	DragAndDropSchema,
	DrawingSchema,
	EssaySchema,
	FillBlankWordBankSchema,
	MatchingSchema,
	MultipleChoiceMultipleSchema,
	MultipleChoiceOptionSchema,
	MultipleChoiceSingleSchema,
	OrderingSchema,
	PerformanceSchema,
	ShortAnswerSchema,
	TFFourItemSchema,
	TrueFalse4ItemSchema,
	VietnameseTFScoringSchema,
} from "./core.js";

// English
export {
	ClozeMixedSchema,
	CollocationSchema,
	ConditionalBuilderSchema,
	DialogueCompletionSchema,
	DictationSchema,
	ErrorCorrectionSchema,
	GrammarTransformationSchema,
	IdiomsSchema,
	MatchingVocabularySchema,
	ParaphraseSchema,
	PassiveVoiceSchema,
	PhonicsSchema,
	ReadingComprehensionSchema,
	ReportedSpeechSchema,
	SentenceManipulationSchema,
	TenseTimelineSchema,
	TranslationSchema,
	VocabularyScaffoldedSchema,
	WordAnalysisSchema,
} from "./english.js";
// Gamified
export {
	AdaptiveDifficultySchema,
	BranchingScenarioNodeSchema,
	BranchingScenarioSchema,
	CollaborativeActivitySchema,
	StreakSystemSchema,
	TimedChallengeSchema,
} from "./gamified.js";
// Math/Science
export {
	CodingExerciseSchema,
	DataInterpretationSchema,
	FinancialLiteracySchema,
	GeometricProofSchema,
	LabReportSchema,
	MeasurementSchema,
	StepByStepMathSchema,
} from "./math-science.js";
// Multimedia
export {
	ArtProjectSchema,
	ExperimentDocumentationSchema,
	FieldTripJournalSchema,
	MultimediaAudioSchema,
	MultimediaPhotoSchema,
	MultimediaVideoSchema,
	ParentChildActivitySchema,
} from "./multimedia.js";
