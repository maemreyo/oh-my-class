import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderManifest, RenderServices } from "../core/types.js";

const childArtifactSchema = z.object({
  id: z.string().min(1).optional(),
  kind: z.string().min(1).refine((kind) => kind !== "teaching_pack", "Nested teaching_pack children are not supported."),
  input: z.unknown(),
});

const teachingPackInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  children: z.array(childArtifactSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type TeachingPackInput = z.infer<typeof teachingPackInputSchema>;

type TeachingPackTemplateData = Omit<TeachingPackInput, "children"> & {
  readonly children: readonly {
    readonly id: string;
    readonly kind: string;
    readonly html: string;
    readonly manifest: RenderManifest;
  }[];
  readonly childManifests: readonly RenderManifest[];
  readonly childManifestJson: string;
  readonly themeCSS: string;
  readonly lang: string;
};

function childContext(parent: RenderContext, child: { readonly id?: string; readonly kind: string }): RenderContext {
  return {
    ...parent,
    requestId: `${parent.requestId}:${child.id ?? child.kind}`,
  };
}

async function adaptTeachingPack(input: unknown, context: RenderContext, services: RenderServices): Promise<TeachingPackTemplateData> {
  const teachingPack = teachingPackInputSchema.parse(input);
  const children = await Promise.all(teachingPack.children.map(async (child, index) => {
    const response = await services.renderChild({ kind: child.kind, input: child.input, context: childContext(context, child) });
    return {
      id: child.id ?? `${child.kind}-${index + 1}`,
      kind: child.kind,
      html: response.html,
      manifest: response.manifest,
    };
  }));
  const childManifests = children.map((child) => child.manifest);

  return {
    title: teachingPack.title,
    subject: teachingPack.subject,
    gradeLevel: teachingPack.gradeLevel,
    theme: teachingPack.theme,
    lang: teachingPack.lang ?? context.locale,
    themeCSS: services.themeCss,
    children,
    childManifests,
    childManifestJson: JSON.stringify(childManifests, null, 2),
  };
}

export const teachingPackPlugin: ArtifactKindPlugin<TeachingPackTemplateData> = {
  kind: "teaching_pack",
  version: "0.1.0",
  templateVersion: "teaching-pack-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: teachingPackInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: { version: "teaching-pack-policy-v1" },
  adapt: adaptTeachingPack,
  templatePath: () => "pages/teaching_pack",
};
