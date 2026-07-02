import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const infographicItemSchema = z.object({
  icon: z.string().optional(),
  label: z.string().optional(),
  value: z.string().optional(),
});

const infographicSectionSchema = z.object({
  title: z.string().min(1),
  content: z.string().min(1),
  svgContent: z.string().optional(),
  items: z.array(infographicItemSchema).optional(),
});

const infographicInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  sections: z.array(infographicSectionSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type InfographicInput = z.infer<typeof infographicInputSchema>;

type InfographicTemplateData = InfographicInput & {
  readonly themeCSS: string;
  readonly lang: string;
};

const infographicSanitizerPolicy = { version: "infographic-policy-v1", config: "infographic" } as const;

function adaptInfographic(input: unknown, context: RenderContext, services: RenderServices): InfographicTemplateData {
  const infographic = infographicInputSchema.parse(input);
  return { ...infographic, themeCSS: services.themeCss, lang: infographic.lang ?? context.locale };
}

export const infographicPlugin: ArtifactKindPlugin<InfographicTemplateData> = {
  kind: "infographic",
  version: "0.1.0",
  templateVersion: "infographic-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: infographicInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: infographicSanitizerPolicy,
  adapt: adaptInfographic,
  templatePath: () => "pages/infographic",
};
