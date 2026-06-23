/**
 * @deprecated This file is HAND-WRITTEN. The canonical Zod schema is now
 * auto-generated in ./generated/lesson_plan.ts from Pydantic models.
 * This file will be removed after migration. Use generated version instead.
 */

import { z } from "zod";

export const LearningObjectiveSchema = z.object({
	description: z.string().min(1),
	bloom_level: z.enum([
		"remember",
		"understand",
		"apply",
		"analyze",
		"evaluate",
		"create",
	]),
	assessment_method: z.string().nullable().optional(),
});

export const LessonPlanSchema = z.object({
	topic: z.string().min(1).max(200),
	grade_level: z.string(),
	subject: z.string(),
	duration_minutes: z.number().int().min(10).max(180),
	learning_objectives: z.array(LearningObjectiveSchema).min(1).max(10),
	prerequisite_knowledge: z.array(z.string()).default([]),
	learning_plan: z.record(z.unknown()).default({}),
	assessment_checkpoints: z
		.array(
			z.object({
				type: z.string(),
				description: z.string(),
				trigger: z.string().nullable().optional(),
			}),
		)
		.default([]),
});

export type LearningObjective = z.infer<typeof LearningObjectiveSchema>;
export type LessonPlan = z.infer<typeof LessonPlanSchema>;
