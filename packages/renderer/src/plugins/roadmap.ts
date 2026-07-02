import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const componentSchema = z.object({ type: z.string().min(1) }).catchall(z.unknown());
const statCardSchema = z.object({ label: z.string().min(1), value: z.string().min(1), variant: z.union([z.literal("target"), z.literal("now"), z.literal("default")]).optional() });

const roadmapInputSchema = z.object({
  title: z.string().min(1),
  theme: z.string().optional(),
  hero: z.object({
    eyebrow: z.string().optional(),
    title: z.string().min(1),
    lede: z.string().optional(),
    stamp: z.string().optional(),
    stats: z.array(statCardSchema).optional(),
  }),
  sections: z.array(z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    subtitle: z.string().optional(),
    tag_num: z.string().optional(),
    components: z.array(componentSchema).optional(),
  })).optional(),
  sidebar: z.object({
    title: z.string().min(1),
    subtitle: z.string(),
    stats: z.array(statCardSchema).optional(),
    nav: z.array(z.object({ label: z.string().min(1), href: z.string().min(1), group: z.string().optional() })).optional(),
    legend: z.array(z.object({ color: z.string().min(1), label: z.string().min(1) })).optional(),
  }),
  accessibility: z.object({ language: z.string().optional() }).optional(),
});

type RoadmapInput = z.infer<typeof roadmapInputSchema>;

type RoadmapTemplateData = RoadmapInput & {
  readonly themeCSS: string;
  readonly lang: string;
};

const roadmapSanitizerPolicy = { version: "roadmap-policy-v1" };

function adaptRoadmap(input: unknown, context: RenderContext, services: RenderServices): RoadmapTemplateData {
  const roadmap = roadmapInputSchema.parse(input);
  return { ...roadmap, lang: roadmap.accessibility?.language ?? context.locale, themeCSS: services.themeCss };
}

export const roadmapPlugin: ArtifactKindPlugin<RoadmapTemplateData> = {
  kind: "roadmap",
  version: "0.1.0",
  templateVersion: "roadmap-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: roadmapInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: roadmapSanitizerPolicy,
  adapt: adaptRoadmap,
  templatePath: () => "pages/roadmap",
};
