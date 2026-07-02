import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const recapItemSchema = z.object({
  id: z.string().min(1),
  concept: z.string().min(1),
  summary: z.string().min(1),
  example: z.string().optional(),
  category: z.string().optional(),
});

const recapInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  items: z.array(recapItemSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type RecapInput = z.infer<typeof recapInputSchema>;

type RecapTemplateData = RecapInput & {
  readonly themeCSS: string;
  readonly lang: string;
};

function adaptRecap(input: unknown, context: RenderContext, services: RenderServices): RecapTemplateData {
  const recap = recapInputSchema.parse(input);
  return { ...recap, themeCSS: services.themeCss, lang: recap.lang ?? context.locale };
}

export const recapPlugin: ArtifactKindPlugin<RecapTemplateData> = {
  kind: "recap",
  version: "0.1.0",
  templateVersion: "recap-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: recapInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: { version: "recap-policy-v1" },
  adapt: adaptRecap,
  templatePath: () => "pages/recap",
};
