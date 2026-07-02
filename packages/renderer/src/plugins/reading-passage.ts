import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const optionSchema = z.object({ label: z.string().min(1), text: z.string().min(1) });

const comprehensionQuestionSchema = z.object({
  id: z.string().min(1),
  prompt: z.string().min(1),
  answer: z.string().min(1),
  type: z.union([z.literal("mc"), z.literal("short_answer"), z.literal("essay")]),
  options: z.array(optionSchema).optional(),
});

const readingPassageInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  passage: z.string().min(1),
  questions: z.array(comprehensionQuestionSchema).min(1),
  author: z.string().optional(),
  source: z.string().optional(),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type ReadingPassageInput = z.infer<typeof readingPassageInputSchema>;

type ReadingPassageTemplateData = Omit<ReadingPassageInput, "questions"> & {
  readonly questions: readonly {
    readonly id: string;
    readonly prompt: string;
    readonly type: "mc" | "short_answer" | "essay";
    readonly options?: readonly { readonly label: string; readonly text: string }[];
  }[];
  readonly themeCSS: string;
  readonly lang: string;
};

const readingPassageSanitizerPolicy = { version: "reading-passage-policy-v1", config: "quiz" } as const;

function adaptReadingPassage(input: unknown, context: RenderContext, services: RenderServices): ReadingPassageTemplateData {
  const passage = readingPassageInputSchema.parse(input);
  return {
    ...passage,
    lang: passage.lang ?? context.locale,
    themeCSS: services.themeCss,
    questions: passage.questions.map((question) => ({
      id: question.id,
      prompt: question.prompt,
      type: question.type,
      options: question.options,
    })),
  };
}

export const readingPassagePlugin: ArtifactKindPlugin<ReadingPassageTemplateData> = {
  kind: "reading_passage",
  version: "0.1.0",
  templateVersion: "reading-passage-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: readingPassageInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: readingPassageSanitizerPolicy,
  adapt: adaptReadingPassage,
  templatePath: () => "pages/reading_passage",
};
