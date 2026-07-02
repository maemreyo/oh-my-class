import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext } from "../core/types.js";

const fixtureInputSchema = z.object({
  title: z.string().min(1),
  body: z.string().min(1),
});

type FixtureTemplateData = {
  readonly title: string;
  readonly body: string;
  readonly lang: string;
  readonly type: string;
  readonly themeCSS: string;
  readonly requestId: string;
  readonly renderMode: string;
};

function adaptFixture(input: unknown, context: RenderContext, services: { readonly themeCss: string }): FixtureTemplateData {
  const fixtureInput = fixtureInputSchema.parse(input);
  return {
    title: fixtureInput.title,
    body: `<section class="fixture-plugin"><p>${fixtureInput.body}</p></section>`,
    lang: context.locale,
    type: "fixture",
    themeCSS: services.themeCss,
    requestId: context.requestId,
    renderMode: context.renderMode,
  };
}

export const fixturePlugin: ArtifactKindPlugin<FixtureTemplateData> = {
  kind: "fixture.echo",
  version: "0.1.0",
  templateVersion: "fixture-template-v1",
  themeVersion: "theme-loader-v1",
  schema: fixtureInputSchema,
  audience: { supported: ["teacher"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: { version: "legacy-sanitize-html-v1" },
  adapt: adaptFixture,
  templatePath: () => "fixture/echo",
};
