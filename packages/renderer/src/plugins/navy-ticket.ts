import { z } from "zod";

import { adaptNavyTicketPractice, adaptNavyTicketTeaching } from "../artifact-ui/adapters/index.js";
import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const anchorCardSchema = z.object({
  word: z.string().min(1),
  impression_vi: z.string().min(1),
  core_trigger_en: z.string().min(1),
  visual_cue_vi: z.string().min(1),
  semantic_chain: z.array(z.string()).min(1),
  example_en: z.string().min(1),
  contrast_note_vi: z.string().min(1),
  student_explanation_vi: z.string().min(1),
  teacher_script_vi: z.string().min(1),
  edge_cases: z.array(z.string()).default([]),
  source_notes: z.array(z.string()).default([]),
});

const semanticAnchorClusterSchema = z.object({
  cluster_id: z.string().min(1),
  title: z.string().min(1),
  title_confidence: z.number().min(0).max(1),
  raw_input_span: z.string().min(1),
  terms: z.array(z.string()).min(2),
  anchors: z.array(anchorCardSchema).min(1),
  contrast_notes: z.array(z.string()).min(1),
  summary_rows: z.array(z.string()).min(1),
  review_status: z.union([z.literal("passed"), z.literal("needs_review"), z.literal("failed")]),
  warnings: z.array(z.string()).default([]),
  teacher_source_notes: z.array(z.string()).default([]),
});

const practiceItemSchema = z.object({
  item_id: z.string().min(1),
  intent: z.union([
    z.literal("core_trigger_recall"),
    z.literal("context_discrimination"),
    z.literal("boundary_explanation"),
    z.literal("reverse_retrieval"),
  ]),
  prompt: z.string().min(1),
  answer: z.string().min(1),
  rationale: z.string().min(1),
});

const practiceSetSchema = z.object({
  practice_set_id: z.string().min(1),
  cluster_id: z.string().min(1),
  items: z.array(practiceItemSchema).min(1),
});

const navyTicketTeachingInputSchema = z.object({
  cluster: semanticAnchorClusterSchema,
  lang: z.string().optional(),
});

const navyTicketPracticeInputSchema = z.object({
  cluster: semanticAnchorClusterSchema,
  practiceSet: practiceSetSchema,
  lang: z.string().optional(),
});

const navyTicketSanitizerPolicy = { version: "navy-ticket-policy-v1", config: "artifact_ui" } as const;

function adaptTeaching(input: unknown, context: RenderContext, services: RenderServices) {
  const parsed = navyTicketTeachingInputSchema.parse(input);
  return adaptNavyTicketTeaching(parsed.cluster, context.audience, services.themeCss, parsed.lang ?? context.locale);
}

function adaptPractice(input: unknown, context: RenderContext, services: RenderServices) {
  const parsed = navyTicketPracticeInputSchema.parse(input);
  return adaptNavyTicketPractice(parsed.cluster, parsed.practiceSet, context.audience, services.themeCss, parsed.lang ?? context.locale);
}

export const navyTicketTeachingPlugin: ArtifactKindPlugin<ReturnType<typeof adaptNavyTicketTeaching>> = {
  kind: "navy-ticket.teaching",
  version: "0.1.0",
  templateVersion: "navy-ticket-teaching-template-v1",
  themeVersion: "theme-resolver-v1",
  familyId: "navy-ticket",
  schema: navyTicketTeachingInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: navyTicketSanitizerPolicy,
  adapt: adaptTeaching,
  templatePath: (context) => `artifact/navy-ticket/teaching.${context.audience}.html`,
};

export const navyTicketPracticePlugin: ArtifactKindPlugin<ReturnType<typeof adaptNavyTicketPractice>> = {
  kind: "navy-ticket.practice",
  version: "0.1.0",
  templateVersion: "navy-ticket-practice-template-v1",
  themeVersion: "theme-resolver-v1",
  familyId: "navy-ticket",
  schema: navyTicketPracticeInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: navyTicketSanitizerPolicy,
  adapt: adaptPractice,
  templatePath: (context) => `artifact/navy-ticket/practice.${context.audience}.html`,
};

export type NavyTicketTeachingInput = z.infer<typeof navyTicketTeachingInputSchema>;
export type NavyTicketPracticeInput = z.infer<typeof navyTicketPracticeInputSchema>;
