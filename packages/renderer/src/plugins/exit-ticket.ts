import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const optionSchema = z.object({ label: z.string().min(1), text: z.string().min(1) });

const exitTicketQuestionSchema = z.object({
  id: z.string().min(1),
  prompt: z.string().min(1),
  type: z.union([z.literal("mc"), z.literal("short_answer"), z.literal("rating")]),
  options: z.array(optionSchema).optional(),
});

const exitTicketInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  questions: z.array(exitTicketQuestionSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type ExitTicketInput = z.infer<typeof exitTicketInputSchema>;

type ExitTicketTemplateData = ExitTicketInput & {
  readonly themeCSS: string;
  readonly lang: string;
};

const exitTicketSanitizerPolicy = { version: "exit-ticket-policy-v1", config: "quiz" } as const;

function adaptExitTicket(input: unknown, context: RenderContext, services: RenderServices): ExitTicketTemplateData {
  const exitTicket = exitTicketInputSchema.parse(input);
  return { ...exitTicket, lang: exitTicket.lang ?? context.locale, themeCSS: services.themeCss };
}

export const exitTicketPlugin: ArtifactKindPlugin<ExitTicketTemplateData> = {
  kind: "exit_ticket",
  version: "0.1.0",
  templateVersion: "exit-ticket-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: exitTicketInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: exitTicketSanitizerPolicy,
  adapt: adaptExitTicket,
  templatePath: () => "pages/exit_ticket",
};
