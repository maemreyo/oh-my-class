import { mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { describe, expect, it } from "vitest";
import { z } from "zod";

import {
  RendererError,
  RendererErrorCode,
  ThemeResolver,
  createPluginRegistry,
  enforceInlineOnlyAssetPolicy,
  hashManagedScriptSource,
  render,
  sanitizeRenderedHtml,
} from "../src/renderer.js";
import type { ArtifactKindPlugin, RenderContext } from "../src/renderer.js";

const context: RenderContext = {
  audience: "teacher",
  locale: "en",
  theme: "high-contrast-dyslexia",
  renderMode: "preview",
  requestId: "policy-test-001",
  versions: { rendererVersion: "test-renderer" },
  assetPolicy: "inline-only",
};

const htmlInputSchema = z.object({ title: z.string().min(1), body: z.string() });

type HtmlTemplateData = {
  readonly title: string;
  readonly body: string;
  readonly lang: string;
  readonly type: string;
  readonly themeCSS: string;
};

function htmlPlugin(body: string): ArtifactKindPlugin<HtmlTemplateData> {
  return {
    kind: "policy.html",
    version: "policy-v1",
    templateVersion: "base-v1",
    themeVersion: "theme-v1",
    schema: htmlInputSchema,
    audience: { supported: ["teacher"] },
    capabilities: { supportsPrint: true },
    sanitizerPolicy: { version: "policy-v1" },
    adapt: (input, renderContext, services) => {
      const parsed = htmlInputSchema.parse(input);
      return {
        title: parsed.title,
        body,
        lang: renderContext.locale,
        type: "policy",
        themeCSS: services.themeCss,
      };
    },
    templatePath: () => "base",
  };
}

function expectRendererError(error: unknown, code: RendererErrorCode): void {
  expect(error).toBeInstanceOf(RendererError);
  if (error instanceof RendererError) expect(error.code).toBe(code);
}

describe("renderer theme sanitizer and asset policy", () => {
  it("applies high-contrast dyslexia theme through ThemeResolver for regular and artifact-ui families", () => {
    const resolver = new ThemeResolver();

    const regular = resolver.resolve({ themeId: "high-contrast-dyslexia", renderMode: "preview", locale: "en" });
    const artifactUi = resolver.resolve({ themeId: "high-contrast-dyslexia", familyId: "paper-dossier", renderMode: "preview", locale: "en" });

    expect(regular.css).toContain("Atkinson Hyperlegible");
    expect(artifactUi.css).toContain("Atkinson Hyperlegible");
    expect(artifactUi.css).toContain("paper-dossier");
    expect(regular.cacheKey).toBe("high-contrast-dyslexia:regular:preview:en");
  });

  it("sanitizes full documents and fragments through one chokepoint", () => {
    const document = '<!DOCTYPE html><html><body><p onclick="alert(1)">Safe</p><iframe src="x"></iframe></body></html>';
    const fragment = '<p onclick="alert(1)">Safe</p><script>alert(1)</script>';

    expect(sanitizeRenderedHtml(document, { version: "test" })).toContain("<p>Safe</p>");
    expect(sanitizeRenderedHtml(document, { version: "test" })).not.toContain("iframe");
    expect(sanitizeRenderedHtml(fragment, { version: "test" })).toBe("<p>Safe</p>");
  });

  it("rejects external src href css urls fonts and script src", () => {
    const samples = [
      '<img src="https://example.test/x.png">',
      '<a href="https://example.test">x</a>',
      '<style>.x{background:url(https://example.test/x.png)}</style>',
      '<style>@import url(https://example.test/x.css)</style>',
      '<style>@font-face{src:url(https://example.test/font.woff2)}</style>',
      '<script src="https://example.test/app.js"></script>',
    ] as const;

    for (const html of samples) {
      expect(() => enforceInlineOnlyAssetPolicy(html)).toThrow(RendererError);
    }
  });

  it("rejects unmanaged inline scripts after rendering", async () => {
    const registry = createPluginRegistry([htmlPlugin('<script>console.log("x")</script>')]);

    await expect(render({ kind: "policy.html", input: { title: "Policy", body: "" }, context }, { registry })).rejects.toSatisfy((error: unknown) => {
      expectRendererError(error, RendererErrorCode.ExternalAsset);
      return true;
    });
  });

  it("allows declared managed inline scripts only when source hash matches", () => {
    const source = 'console.log("managed")';
    const dir = mkdtempSync(join(tmpdir(), "omc-managed-script-"));
    const sourcePath = join(dir, "managed.js");
    writeFileSync(sourcePath, source, "utf8");
    const declaration = { id: "managed-demo", sourcePath, sha256: hashManagedScriptSource(source) };

    expect(() => enforceInlineOnlyAssetPolicy(`<script data-managed-script-id="managed-demo">${source}</script>`, [declaration])).not.toThrow();
    expect(() => enforceInlineOnlyAssetPolicy('<script data-managed-script-id="managed-demo">console.log("changed")</script>', [declaration])).toThrow(RendererError);
  });
});
