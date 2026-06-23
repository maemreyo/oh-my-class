/**
 * Schemas — AUTO-GENERATED from Pydantic models (common/contracts/)
 * Source of truth: common/contracts/*.py
 * Regenerate: python scripts/generate_zod_schemas.py
 *
 * Hand-written types (questions.ts, quiz.ts) are NOT generated — they stay manual.
 */

// Generated Zod schemas from Pydantic
export {
  LessonPlanSchema,
  type LessonPlan,
  type LearningObjective,
} from "./generated/lesson_plan.js";

export {
  ArtifactContentSchema,
  type ArtifactContent,
} from "./generated/artifact.js";

// Hand-written question types (not from Pydantic)
export {
  QuestionTypeSchema,
  type QuestionType,
  CoreQuestionTypes,
  EnglishQuestionTypes,
  MathScienceQuestionTypes,
  MultimediaQuestionTypes,
  GamifiedQuestionTypes,
} from "./questions.js";

// Exercise type schemas
export * from "./exercise-types/index.js";

// Legacy re-exports — will be removed after migration
export { LessonPlanSchema as LessonPlanSchemaLegacy } from "./lesson_plan.js";
export { ArtifactContentSchema as ArtifactContentSchemaLegacy } from "./artifact.js";
