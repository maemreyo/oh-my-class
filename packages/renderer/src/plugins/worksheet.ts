import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const worksheetQuestionSchema = z.object({
  id: z.string().min(1),
  prompt: z.string().min(1),
  type: z.string().min(1),
  answer: z.string().optional(),
  explanation: z.string().optional(),
  teacher_only: z.unknown().optional(),
});

const worksheetSectionSchema = z.object({
  title: z.string().min(1),
  instructions: z.string().optional(),
  questions: z.array(worksheetQuestionSchema).min(1),
  teacher_only: z.unknown().optional(),
});

const worksheetInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  sections: z.array(worksheetSectionSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type WorksheetInput = z.infer<typeof worksheetInputSchema>;

type WorksheetTemplateData = Omit<WorksheetInput, "sections"> & {
  readonly sections: readonly {
    readonly title: string;
    readonly instructions?: string;
    readonly questions: readonly {
      readonly id: string;
      readonly prompt: string;
      readonly type: string;
    }[];
  }[];
  readonly themeCSS: string;
  readonly lang: string;
};

function adaptWorksheet(input: unknown, context: RenderContext, services: RenderServices): WorksheetTemplateData {
  const worksheet = worksheetInputSchema.parse(input);
  return {
    title: worksheet.title,
    subject: worksheet.subject,
    gradeLevel: worksheet.gradeLevel,
    theme: worksheet.theme,
    lang: worksheet.lang ?? context.locale,
    themeCSS: services.themeCss,
    sections: worksheet.sections
      .filter((section) => section.teacher_only !== true)
      .map((section) => ({
        title: section.title,
        instructions: section.instructions,
        questions: section.questions
          .filter((question) => question.teacher_only !== true)
          .map((question) => ({ id: question.id, prompt: question.prompt, type: question.type })),
      })),
  };
}

export const worksheetPlugin: ArtifactKindPlugin<WorksheetTemplateData> = {
  kind: "worksheet",
  version: "0.1.0",
  templateVersion: "worksheet-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: worksheetInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: { version: "worksheet-policy-v1" },
  adapt: adaptWorksheet,
  templatePath: () => "pages/worksheet",
};
