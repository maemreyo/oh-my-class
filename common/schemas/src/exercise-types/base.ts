import { z } from "zod";

/**
 * Base schemas shared across ALL exercise types.
 * Source: doc 06 §9 Master Schema
 */

export const DifficultySchema = z.enum([
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create",
]);

export const BloomLevelVNSchema = z.enum([
  "nhan_biet",
  "thong_hieu",
  "van_dung",
  "van_dung_cao",
]);

export const MetadataSchema = z.object({
  subject: z.string(),
  grade: z.number().int().min(1).max(12),
  topic: z.string(),
  lessonId: z.string().optional(),
  estimatedTimeSeconds: z.number().int().optional(),
  author: z.string().optional(),
  createdAt: z.string().optional(),
  updatedAt: z.string().optional(),
});

export const BaseQuestionSchema = z.object({
  id: z.string(),
  type: z.string(),
  difficulty: DifficultySchema,
  bloomLevel: BloomLevelVNSchema.optional(),
  tags: z.array(z.string()).default([]),
  metadata: MetadataSchema,
});

export const ScoringConfigSchema = z.object({
  type: z.enum(["all_or_nothing", "partial_credit", "vietnamese_tf_2025"]),
  pointsTotal: z.number().optional(),
  penaltyPerWrong: z.number().optional(),
});

export const RubricCriterionSchema = z.object({
  name: z.string(),
  weight: z.number().min(0).max(100),
  levels: z
    .array(
      z.object({
        score: z.number(),
        description: z.string(),
      }),
    )
    .optional(),
  descriptors: z.record(z.string(), z.string()).optional(),
});

export const RubricSchema = z.object({
  criteria: z.array(RubricCriterionSchema),
});

export type Difficulty = z.infer<typeof DifficultySchema>;
export type BloomLevelVN = z.infer<typeof BloomLevelVNSchema>;
export type BaseQuestion = z.infer<typeof BaseQuestionSchema>;
export type ScoringConfig = z.infer<typeof ScoringConfigSchema>;
export type Rubric = z.infer<typeof RubricSchema>;
