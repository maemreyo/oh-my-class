import { describe, expect, it } from "vitest";

import { render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

const recapInput = {
  title: "Fraction Equivalence Recap",
  subject: "Math",
  gradeLevel: "Grade 5",
  items: [
    { id: "r1", concept: "Equivalent fractions", summary: "Fractions can name the same amount.", example: "1/2 = 2/4", category: "Key idea" },
  ],
} as const;

const infographicInput = {
  title: "Fraction Model Infographic",
  subject: "Math",
  gradeLevel: "Grade 5",
  sections: [
    {
      title: "Same whole",
      content: "Compare equal-sized wholes before comparing shaded parts.",
      svgContent: '<svg viewBox="0 0 100 20" role="img" aria-label="Two equal bars"><rect x="0" y="0" width="45" height="20" fill="#1d4ed8"></rect><rect x="55" y="0" width="45" height="20" fill="#1d4ed8"></rect></svg>',
      items: [{ icon: "=", label: "Visual rule", value: "Same whole first" }],
    },
  ],
} as const;

function context(kind: "recap" | "infographic", renderMode: RenderContext["renderMode"]): RenderContext {
  return {
    audience: "student",
    locale: "en",
    theme: "default",
    renderMode,
    requestId: `${kind}-${renderMode}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("summary and visual artifact plugins", () => {
  it("declares recap and infographic registry metadata", () => {
    const metadata = rendererPluginMetadata();

    expect(metadata).toContainEqual({
      kind: "recap",
      version: "0.1.0",
      templateVersion: "recap-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "recap-policy-v1",
    });
    expect(metadata).toContainEqual({
      kind: "infographic",
      version: "0.1.0",
      templateVersion: "infographic-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "infographic-policy-v1",
    });
  });

  it("renders recap standalone HTML with a manifest", async () => {
    const response = await render({ kind: "recap", input: recapInput, context: context("recap", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Fraction Equivalence Recap");
    expect(response.html).toContain("Equivalent fractions");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("recap");
    expect(response.html).toMatchSnapshot("recap-student-preview");
  });

  it("renders infographic standalone HTML and preserves safe inline SVG", async () => {
    const response = await render({ kind: "infographic", input: infographicInput, context: context("infographic", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Fraction Model Infographic");
    expect(response.html).toContain("<svg");
    expect(response.html).toContain("<rect");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("infographic");
    expect(response.html).toMatchSnapshot("infographic-student-preview");
  });

  it("supports print mode for both summary and visual plugins", async () => {
    const [recap, infographic] = await Promise.all([
      render({ kind: "recap", input: recapInput, context: context("recap", "print") }),
      render({ kind: "infographic", input: infographicInput, context: context("infographic", "print") }),
    ]);

    expect(recap.html).toContain("@media print");
    expect(infographic.html).toContain("@media print");
  });

  it("rejects invalid summary and visual inputs before rendering", async () => {
    await expect(render({ kind: "recap", input: { ...recapInput, items: [] }, context: context("recap", "preview") })).rejects.toThrow(/validation failed/i);
    await expect(render({ kind: "infographic", input: { ...infographicInput, sections: [] }, context: context("infographic", "preview") })).rejects.toThrow(/validation failed/i);
  });
});
