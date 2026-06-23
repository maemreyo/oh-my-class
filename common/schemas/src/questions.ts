import { z } from "zod";

/**
 * Question type enums — string literals for type discrimination.
 * Individual Zod schemas live in ./exercise-types/
 */

export const CoreQuestionTypes = [
	"multiple_choice_single",
	"multiple_choice_multiple",
	"true_false_4item",
	"short_answer",
	"essay",
	"fill_blank_wordbank",
	"cloze",
	"matching",
	"ordering",
	"drag_and_drop",
	"drawing",
	"performance",
] as const;

/**
 * English Language types (§9.2) — 19 types
 */
export const EnglishQuestionTypes = [
	"vocabulary_scaffolded",
	"cloze_mixed",
	"matching_vocabulary",
	"reading_comprehension",
	"grammar_transformation",
	"error_correction",
	"sentence_manipulation",
	"paraphrase",
	"dialogue_completion",
	"phonics",
	"dictation",
	"translation",
	"idioms",
	"collocation",
	"word_analysis",
	"tense_timeline",
	"conditional_builder",
	"reported_speech",
	"passive_voice",
] as const;

/**
 * Math/Science types (§9.3) — 7 types
 */
export const MathScienceQuestionTypes = [
	"step_by_step_math",
	"geometric_proof",
	"data_interpretation",
	"lab_report",
	"measurement",
	"coding_exercise",
	"financial_literacy",
] as const;

/**
 * Multimedia Homework types (§9.4) — 7 types
 */
export const MultimediaQuestionTypes = [
	"multimedia_video",
	"multimedia_audio",
	"multimedia_photo",
	"experiment_documentation",
	"parent_child_activity",
	"field_trip_journal",
	"art_project",
] as const;

/**
 * Gamified types (§9.6)
 */
export const GamifiedQuestionTypes = [
	"timed_challenge",
	"streak_system",
	"adaptive_difficulty",
	"branching_scenario",
	"collaborative_activity",
] as const;

export const QuestionTypeSchema = z.enum([
	...CoreQuestionTypes,
	...EnglishQuestionTypes,
	...MathScienceQuestionTypes,
	...MultimediaQuestionTypes,
	...GamifiedQuestionTypes,
]);

export type QuestionType = z.infer<typeof QuestionTypeSchema>;

// Re-export all individual schemas
export * from "./exercise-types/index.js";
