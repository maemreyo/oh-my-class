import { z } from "zod";
import {
	BaseQuestionSchema,
	RubricSchema,
	ScoringConfigSchema,
} from "./base.js";

// ── 1.1 Multiple Choice Single ──

export const MultipleChoiceOptionSchema = z.object({
	id: z.string(),
	text: z.string(),
	isCorrect: z.boolean(),
});

export const MultipleChoiceSingleSchema = BaseQuestionSchema.extend({
	type: z.literal("multiple_choice_single"),
	stem: z.string(),
	options: z.array(MultipleChoiceOptionSchema).min(4).max(4),
	explanation: z.string().optional(),
});

// ── 1.2 Multiple Choice Multiple ──

export const MultipleChoiceMultipleSchema = BaseQuestionSchema.extend({
	type: z.literal("multiple_choice_multiple"),
	stem: z.string(),
	options: z.array(MultipleChoiceOptionSchema).min(2),
	scoring: ScoringConfigSchema.optional(),
	explanation: z.string().optional(),
});

// ── 1.3 True/False 4-item (Vietnamese exam format) ──

export const TFFourItemSchema = z.object({
	id: z.string(),
	text: z.string(),
	isTrue: z.boolean(),
});

export const VietnameseTFScoringSchema = z.object({
	type: z.literal("vietnamese_tf_2025"),
	correct1: z.literal(0.1),
	correct2: z.literal(0.25),
	correct3: z.literal(0.5),
	correct4: z.literal(1.0),
});

export const TrueFalse4ItemSchema = BaseQuestionSchema.extend({
	type: z.literal("true_false_4item"),
	stem: z.string(),
	items: z.array(TFFourItemSchema).min(4).max(4),
	scoring: VietnameseTFScoringSchema,
});

// ── 1.4 Short Answer ──

export const ShortAnswerSchema = BaseQuestionSchema.extend({
	type: z.literal("short_answer"),
	stem: z.string(),
	correctAnswer: z.string(),
	acceptableAnswers: z.array(z.string()).default([]),
	tolerance: z.number().nullable().optional(),
	unit: z.string().nullable().optional(),
});

// ── 1.5 Essay ──

export const EssaySchema = BaseQuestionSchema.extend({
	type: z.literal("essay"),
	prompt: z.string(),
	wordLimit: z
		.object({
			min: z.number().int(),
			max: z.number().int(),
		})
		.optional(),
	rubric: RubricSchema.optional(),
});

// ── 1.6 Fill Blank (Word Bank) ──

export const FillBlankWordBankSchema = BaseQuestionSchema.extend({
	type: z.literal("fill_blank_wordbank"),
	context: z.string(),
	blanks: z.array(
		z.object({
			id: z.number().int(),
			correctAnswer: z.string(),
		}),
	),
	wordBank: z.array(z.string()),
	distractors: z.array(z.string()).default([]),
	shuffleWordBank: z.boolean().default(true),
});

// ── 1.7 Cloze (Free) ──

export const ClozeSchema = BaseQuestionSchema.extend({
	type: z.literal("cloze"),
	clozeType: z.enum(["grammar", "vocabulary", "contextual"]),
	passage: z.string(),
	blanks: z.array(
		z.object({
			id: z.number().int(),
			correctAnswer: z.string(),
			hint: z.string().optional(),
		}),
	),
	caseSensitive: z.boolean().default(false),
});

// ── 1.8 Matching ──

export const MatchingSchema = BaseQuestionSchema.extend({
	type: z.literal("matching"),
	instructions: z.string(),
	leftColumn: z.array(z.object({ id: z.string(), text: z.string() })),
	rightColumn: z.array(
		z.object({
			id: z.string(),
			text: z.string(),
			isDistractor: z.boolean().optional(),
		}),
	),
	correctMatches: z.array(
		z.object({
			left: z.string(),
			right: z.string(),
		}),
	),
});

// ── 1.9 Ordering ──

export const OrderingSchema = BaseQuestionSchema.extend({
	type: z.literal("ordering"),
	instructions: z.string(),
	items: z.array(
		z.object({
			id: z.number().int(),
			text: z.string(),
			correctPosition: z.number().int(),
		}),
	),
});

// ── 1.10 Drag and Drop ──

export const DragAndDropSchema = BaseQuestionSchema.extend({
	type: z.literal("drag_and_drop"),
	instructions: z.string(),
	zones: z.array(z.object({ id: z.string(), label: z.string() })),
	draggables: z.array(
		z.object({
			id: z.string(),
			text: z.string(),
			correctZone: z.string(),
			isDistractor: z.boolean().optional(),
		}),
	),
});

// ── 1.11 Drawing ──

export const DrawingSchema = BaseQuestionSchema.extend({
	type: z.literal("drawing"),
	instructions: z.string(),
	canvas: z.object({ width: z.number(), height: z.number() }),
	rubric: RubricSchema.optional(),
});

// ── 1.12 Performance ──

export const PerformanceSchema = BaseQuestionSchema.extend({
	type: z.literal("performance"),
	task: z.string(),
	format: z.enum(["presentation", "experiment", "speech", "project"]),
	timeLimit: z.number().int().optional(),
	rubric: RubricSchema.optional(),
});
