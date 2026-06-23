/**
 * Quiz types — hand-written (no Pydantic equivalent yet)
 */

import { z } from "zod";

/**
 * Quiz difficulty levels (Vietnamese exam standard per QĐ 764)
 */
export const DifficultyLevelSchema = z.enum([
	"nhan_biet", // nhận biết (remember) — 40%
	"thong_hieu", // thông hiểu (understand) — 30%
	"van_dung", // vận dụng (apply+analyze) — 20%
	"van_dung_cao", // vận dụng cao (evaluate+create) — 10%
]);

export const QuizOptionSchema = z.object({
	id: z.string(),
	text: z.string().min(1),
	is_correct: z.boolean(),
});

export const QuizQuestionSchema = z.object({
	id: z.string(),
	question_type: z.string(),
	difficulty: DifficultyLevelSchema,
	bloom_level: z.string(),
	prompt: z.string().min(1),
	options: z.array(QuizOptionSchema).optional(),
	correct_answer: z.string().optional(),
	explanation: z.string().optional(),
	points: z.number().min(0).default(1),
	time_limit_seconds: z.number().int().min(0).optional(),
});

export const QuizSchema = z.object({
	title: z.string().min(1).max(200),
	subject: z.string(),
	topic: z.string(),
	grade_level: z.string(),
	questions: z.array(QuizQuestionSchema).min(1),
	time_limit_minutes: z.number().int().min(1).optional(),
	total_points: z.number().int().min(1),
	instructions: z.string().optional(),
});

export type DifficultyLevel = z.infer<typeof DifficultyLevelSchema>;
export type QuizOption = z.infer<typeof QuizOptionSchema>;
export type QuizQuestion = z.infer<typeof QuizQuestionSchema>;
export type Quiz = z.infer<typeof QuizSchema>;
