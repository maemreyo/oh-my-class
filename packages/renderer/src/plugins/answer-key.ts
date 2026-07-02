import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const componentSchema = z.object({ type: z.string().min(1) }).catchall(z.unknown());

const answerKeySectionSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  sub: z.string().optional(),
  range: z.string().optional(),
  group: z.string().optional(),
  instruction: z.string().optional(),
  summary: z.string().optional(),
  components: z.array(componentSchema).optional(),
});

const answerKeyInputSchema = z.object({
  title: z.string().min(1),
  theme: z.string().optional(),
  sections: z.array(answerKeySectionSchema).optional(),
  metadata: z.object({
    total_questions: z.number().int().positive().optional(),
    groups: z.record(z.string(), z.object({ label: z.string(), color: z.string().optional() })).optional(),
    hero_stats: z.array(z.object({ label: z.string(), value: z.string(), unit: z.string().optional() })).optional(),
  }).optional(),
  accessibility: z.object({ language: z.string().optional() }).optional(),
});

type AnswerKeyInput = z.infer<typeof answerKeyInputSchema>;

type AnswerKeyTemplateData = AnswerKeyInput & {
  readonly themeCSS: string;
  readonly lang: string;
};

const answerKeySanitizerPolicy = { version: "answer-key-policy-v1", config: "answer_key" } as const;

function adaptAnswerKey(input: unknown, context: RenderContext, services: RenderServices): AnswerKeyTemplateData {
  const answerKey = answerKeyInputSchema.parse(input);
  return {
    ...answerKey,
    lang: answerKey.accessibility?.language ?? context.locale,
    themeCSS: services.themeCss,
  };
}

export const answerKeyPlugin: ArtifactKindPlugin<AnswerKeyTemplateData> = {
  kind: "answer_key",
  version: "0.1.0",
  templateVersion: "answer-key-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: answerKeyInputSchema,
  audience: { supported: ["teacher"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: answerKeySanitizerPolicy,
  adapt: adaptAnswerKey,
  templatePath: () => "pages/answer_key",
};
