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
export { LessonPlanSchema as LessonPlanSchemaLegacy } from "./lesson_plan.js";
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
