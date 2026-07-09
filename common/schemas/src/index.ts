/**
 * Schemas — AUTO-GENERATED from Pydantic models (common/contracts/)
 * Source of truth: common/contracts/*.py
 * Regenerate: python scripts/generate_zod_schemas.py
 *
 * Hand-written types (questions.ts, quiz.ts) are NOT generated — they stay manual.
 */

export { ArtifactContentSchema as ArtifactContentSchemaLegacy } from "./artifact.js";
// Error schemas
export {
	type ErrorCode,
	ErrorCodeSchema,
	type ErrorResponse,
	ErrorResponseSchema,
	type PipelineErrorResponse,
	PipelineErrorResponseSchema,
	type ValidationErrorDetail,
	ValidationErrorDetailSchema,
} from "./error.js";
// Exercise type schemas
export * from "./exercise-types/index.js";
export {
	type ArtifactContent,
	ArtifactContentSchema,
} from "./generated/artifact.js";
// Generated Zod schemas from Pydantic
	export {
	type LearningObjective,
	type LessonPlan,
	type MethodologyMetadata,
	type MethodologyPayloads,
	LessonPlanSchema,
	MethodologyMetadataSchema,
	MethodologyPayloadsSchema,
} from "./generated/lesson_plan.js";
export {
	type InverseThinkingPack,
	InverseThinkingPackSchema,
} from "./generated/inverse_thinking.js";
export {
	METHODOLOGY_REGISTRY,
	type MethodologyRegistryEntry,
	type MethodologyRegistryTag,
} from "./generated/methodology_registry.js";
export {
	AmbiguousVocabularyClusterSchema,
	AnchorCardSchema,
	PracticeItemSchema,
	PracticeSetSchema,
	InputNormalizationReportSchema,
	SemanticAnchorClusterSchema,
	NormalizedVocabularyClusterSchema,
	type AmbiguousVocabularyCluster,
	type AnchorCard,
	type InputNormalizationReport,
	type NormalizedVocabularyCluster,
	type PracticeItem,
	type PracticeSet,
	type SemanticAnchorCluster,
} from "./generated/vocabulary_batch.js";
export {
	VocabularyClusterEvidenceEntrySchema,
	VocabularyClusterWorkflowSchema,
	type VocabularyClusterEvidenceEntry,
	type VocabularyClusterWorkflow,
} from "./generated/vocabulary_cluster_workflow.js";
export { LessonPlanSchema as LessonPlanSchemaLegacy } from "./lesson_plan.js";
// Slide deck contract (SDE-02/SDE-03): types mirror the Python contract for
// the app editor (apps/web); the schemas back drift-check tests that keep
// hardcoded field bounds (Turbopack can't bundle a value-import of this
// package's TS source for the browser — see apps/web's block-constraints.ts)
// honest against common/contracts/slide_deck.py's pydantic Field(...) constraints.
export {
	type SlideDeckData,
	SlideDeckDataSchema,
	type SlideDeckSlide,
	SlideDeckSlideSchema,
	type SlideDeckBlock,
	SlideDeckBlockSchema,
	type SlideDeckMedia,
	SlideDeckMediaSchema,
	type SlideDeckInteraction,
	SlideDeckInteractionSchema,
	type SlideDeckInteractionOption,
	SlideDeckInteractionOptionSchema,
	type SlideDeckInteractionTeacherOnly,
	SlideDeckInteractionTeacherOnlySchema,
	type SlideDeckTeacherOnly,
	SlideDeckTeacherOnlySchema,
} from "./generated/slide_deck.js";
// Log context schemas
export {
	type LogContext,
	LogContextSchema,
} from "./log-context.js";
// Run and Artifact API response types (match gateway RunResponse + ArtifactContent+rendered)
export {
	type Run,
	RunSchema,
	type Artifact,
	ArtifactSchema,
} from "./run.js";
// Hand-written question types (not from Pydantic)
export {
	CoreQuestionTypes,
	EnglishQuestionTypes,
	GamifiedQuestionTypes,
	MathScienceQuestionTypes,
	MultimediaQuestionTypes,
	type QuestionType,
	QuestionTypeSchema,
} from "./questions.js";
