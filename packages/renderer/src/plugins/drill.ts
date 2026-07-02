import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const drillOptionSchema = z.object({
  label: z.string().min(1),
  text: z.string().min(1),
});

const drillQuestionSchema = z.object({
  id: z.string().min(1),
  prompt: z.string().min(1),
  answer: z.string().min(1),
  explanation: z.string().optional(),
  type: z.union([z.literal("mc"), z.literal("fill"), z.literal("tf")]),
  options: z.array(drillOptionSchema).optional(),
  timeMinutes: z.number().positive().optional(),
  teacher_only: z.unknown().optional(),
});

const drillInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  questions: z.array(drillQuestionSchema).min(1),
  timeLimit: z.number().positive().optional(),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type DrillInput = z.infer<typeof drillInputSchema>;

type DrillTemplateData = Omit<DrillInput, "questions"> & {
  readonly questions: readonly {
    readonly id: string;
    readonly prompt: string;
    readonly type: "mc" | "fill" | "tf";
    readonly options?: readonly { readonly label: string; readonly text: string }[];
    readonly timeMinutes?: number;
  }[];
  readonly themeCSS: string;
  readonly lang: string;
};

const drillSanitizerPolicy = { version: "drill-policy-v1", config: "quiz" } as const;

function adaptDrill(input: unknown, context: RenderContext, services: RenderServices): DrillTemplateData {
  const drill = drillInputSchema.parse(input);
  return {
    title: drill.title,
    subject: drill.subject,
    gradeLevel: drill.gradeLevel,
    timeLimit: drill.timeLimit,
    theme: drill.theme,
    lang: drill.lang ?? context.locale,
    themeCSS: services.themeCss,
    questions: drill.questions
      .filter((question) => question.teacher_only !== true)
      .map((question) => ({
        id: question.id,
        prompt: question.prompt,
        type: question.type,
        options: question.options,
        timeMinutes: question.timeMinutes,
      })),
  };
}

export const drillPlugin: ArtifactKindPlugin<DrillTemplateData> = {
  kind: "drill",
  version: "0.1.0",
  templateVersion: "drill-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: drillInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: drillSanitizerPolicy,
  adapt: adaptDrill,
  templatePath: () => "pages/drill",
};
