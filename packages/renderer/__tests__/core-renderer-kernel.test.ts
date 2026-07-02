import { describe, expect, it } from "vitest";
import { z } from "zod";

import {
  RendererError,
  RendererErrorCode,
  createPluginRegistry,
  render,
  renderBatch,
  rendererPluginMetadata,
} from "../src/renderer.js";
import type { ArtifactKindPlugin, RenderContext } from "../src/renderer.js";

const context: RenderContext = {
  audience: "teacher",
  locale: "en",
  theme: "default",
  renderMode: "preview",
  requestId: "kernel-test-001",
  versions: { rendererVersion: "test-renderer" },
  assetPolicy: "inline-only",
};

const tinySchema = z.object({ title: z.string().min(1) });

type TinyTemplateData = {
  readonly title: string;
  readonly body: string;
  readonly lang: string;
  readonly type: string;
  readonly themeCSS: string;
};

const tinyPlugin: ArtifactKindPlugin<TinyTemplateData> = {
  kind: "test.tiny",
  version: "tiny-v1",
  templateVersion: "base-v1",
  themeVersion: "theme-v1",
  schema: tinySchema,
  audience: { supported: ["teacher"] },
  capabilities: { supportsPrint: false },
  sanitizerPolicy: { version: "sanitizer-v1" },
  adapt: (input, renderContext, services) => {
    const tinyInput = tinySchema.parse(input);
    return {
      title: tinyInput.title,
      body: `<section><p>${tinyInput.title}</p><p>${renderContext.requestId}</p></section>`,
      lang: renderContext.locale,
      type: "tiny",
      themeCSS: services.themeCss,
    };
  },
  templatePath: () => "base",
};

function expectRendererError(error: unknown, code: RendererErrorCode): void {
  expect(error).toBeInstanceOf(RendererError);
  if (error instanceof RendererError) {
    expect(error.code).toBe(code);
  }
}

describe("core renderer kernel", () => {
  it("renders the fixture plugin with manifest, diagnostics, and metrics", async () => {
    const response = await render({
      kind: "fixture.echo",
      input: { title: "Fixture Kernel", body: "Hello from the fixture plugin." },
      context,
    });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Fixture Kernel");
    expect(response.html).toContain("Hello from the fixture plugin.");
    expect(response.html).toContain("oh-my-class");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("fixture.echo");
    expect(response.manifest.rendererVersion).toBe("test-renderer");
    expect(response.manifest.contentHash).toMatch(/^[a-f0-9]{64}$/);
    expect(response.diagnostics).toEqual([]);
    expect(response.metrics.renderTimeMs).toBeGreaterThanOrEqual(0);
  });

  it("renders batches through the same plugin registry", async () => {
    const responses = await renderBatch({
      requests: [
        { kind: "fixture.echo", input: { title: "First", body: "One" }, context },
        { kind: "fixture.echo", input: { title: "Second", body: "Two" }, context },
      ],
    });

    expect(responses).toHaveLength(2);
    expect(responses[0]?.html).toContain("First");
    expect(responses[1]?.html).toContain("Second");
  });

  it("rejects duplicate plugin kinds", () => {
    expect(() => createPluginRegistry([tinyPlugin, tinyPlugin])).toThrow(RendererError);
  });

  it("exposes registered plugin metadata", () => {
    const metadata = rendererPluginMetadata();

    expect(metadata).toContainEqual({
      kind: "fixture.echo",
      version: "0.1.0",
      templateVersion: "fixture-template-v1",
      themeVersion: "theme-loader-v1",
      supportedAudiences: ["teacher"],
      supportsPrint: true,
      sanitizerPolicyVersion: "legacy-sanitize-html-v1",
    });
  });

  it("returns typed unknown-kind errors", async () => {
    await expect(render({ kind: "missing.kind", input: {}, context })).rejects.toSatisfy((error: unknown) => {
      expectRendererError(error, RendererErrorCode.UnknownKind);
      return true;
    });
  });

  it("returns typed validation errors before adapter execution", async () => {
    await expect(render({ kind: "fixture.echo", input: { title: "" }, context })).rejects.toSatisfy((error: unknown) => {
      expectRendererError(error, RendererErrorCode.ValidationFailed);
      return true;
    });
  });

  it("rejects unsupported audiences before rendering", async () => {
    await expect(
      render({
        kind: "fixture.echo",
        input: { title: "Student", body: "Unsupported audience" },
        context: { ...context, audience: "student" },
      }),
    ).rejects.toSatisfy((error: unknown) => {
      expectRendererError(error, RendererErrorCode.UnsupportedAudience);
      return true;
    });
  });

  it("rejects external assets after template rendering", async () => {
    const externalAssetPlugin: ArtifactKindPlugin<TinyTemplateData> = {
      ...tinyPlugin,
      kind: "test.external-asset",
      adapt: (input, renderContext, services) => {
        const tinyInput = tinySchema.parse(input);
        return {
          title: tinyInput.title,
          body: '<img src="https://example.test/image.png" alt="external">',
          lang: renderContext.locale,
          type: "external-asset",
          themeCSS: services.themeCss,
        };
      },
    };
    const registry = createPluginRegistry([externalAssetPlugin]);

    await expect(
      render({ kind: externalAssetPlugin.kind, input: { title: "External" }, context }, { registry }),
    ).rejects.toSatisfy((error: unknown) => {
      expectRendererError(error, RendererErrorCode.ExternalAsset);
      return true;
    });
  });
});
