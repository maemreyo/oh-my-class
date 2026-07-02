import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const quizOptionSchema = z.object({
  label: z.string().min(1),
  text: z.string().min(1),
});

const quizQuestionSchema = z.object({
  id: z.string().min(1),
  prompt: z.string().min(1),
  options: z.array(quizOptionSchema).min(1),
  answer: z.string().min(1),
  explain: z.string().optional(),
  timeMinutes: z.number().positive().optional(),
});

const quizInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  timeLimit: z.number().positive().optional(),
  questions: z.array(quizQuestionSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type QuizInput = z.infer<typeof quizInputSchema>;

type QuizTemplateData = QuizInput & {
  readonly themeCSS: string;
  readonly lang: string;
  readonly showAnswers: boolean;
};

function adaptQuiz(input: unknown, context: RenderContext, services: RenderServices): QuizTemplateData {
  const quiz = quizInputSchema.parse(input);
  return {
    ...quiz,
    themeCSS: services.themeCss,
    lang: quiz.lang ?? context.locale,
    showAnswers: context.audience === "teacher",
  };
}

export const quizPlugin: ArtifactKindPlugin<QuizTemplateData> = {
  kind: "quiz",
  version: "0.1.0",
  templateVersion: "quiz-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: quizInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: { version: "quiz-policy-v1", config: "quiz" },
  adapt: adaptQuiz,
  templatePath: () => "pages/quiz",
};
