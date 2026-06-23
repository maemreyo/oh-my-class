import { z } from "zod";
import { BaseQuestionSchema, RubricSchema } from "./base.js";

// ── 4.1 Video Recording ──

export const MultimediaVideoSchema = BaseQuestionSchema.extend({
  type: z.literal("multimedia_video"),
  instructions: z.string(),
  maxDuration: z.number().int(),
  rubric: RubricSchema.optional(),
  aiCheatMitigation: z.string().optional(),
});

// ── 4.2 Audio Recording ──

export const MultimediaAudioSchema = BaseQuestionSchema.extend({
  type: z.literal("multimedia_audio"),
  instructions: z.string(),
  maxDuration: z.number().int(),
  rubric: RubricSchema.optional(),
});

// ── 4.3 Photo Documentation ──

export const MultimediaPhotoSchema = BaseQuestionSchema.extend({
  type: z.literal("multimedia_photo"),
  instructions: z.string(),
  minPhotos: z.number().int().default(1),
  maxPhotos: z.number().int().default(10),
  allowAnnotations: z.boolean().default(true),
  questions: z.array(z.string()),
});

// ── 4.4 Experiment Documentation ──

export const ExperimentDocumentationSchema = BaseQuestionSchema.extend({
  type: z.literal("experiment_documentation"),
  experiment: z.object({
    title: z.string(),
    materials: z.array(z.string()),
    steps: z.array(z.string()),
  }),
  documentationRequirements: z.object({
    photos: z.object({ min: z.number().int() }).optional(),
    video: z.object({ maxDuration: z.number().int() }).optional(),
    writtenReflection: z
      .object({
        prompts: z.array(z.string()),
      })
      .optional(),
  }),
});

// ── 4.5 Parent-Child Activity ──

export const ParentChildActivitySchema = BaseQuestionSchema.extend({
  type: z.literal("parent_child_activity"),
  title: z.string(),
  studentTasks: z.array(
    z.object({
      task: z.string(),
      format: z.string(),
    }),
  ),
  parentTasks: z.array(
    z.object({
      task: z.string(),
    }),
  ),
});

// ── 4.6 Field Trip Journal ──

export const FieldTripJournalSchema = BaseQuestionSchema.extend({
  type: z.literal("field_trip_journal"),
  destination: z.string(),
  sections: z.array(
    z.object({
      name: z.enum(["pre_trip", "during_trip", "post_trip"]),
      prompts: z.array(z.string()).optional(),
      format: z.string().optional(),
      maxEntries: z.number().int().optional(),
    }),
  ),
});

// ── 4.7 Art Project ──

export const ArtProjectSchema = BaseQuestionSchema.extend({
  type: z.literal("art_project"),
  prompt: z.string(),
  documentation: z.object({
    processPhotos: z.object({ min: z.number().int() }).optional(),
    finalPhoto: z.boolean().optional(),
    writtenReflection: z
      .object({
        prompts: z.array(z.string()),
      })
      .optional(),
  }),
  rubric: RubricSchema.optional(),
});
