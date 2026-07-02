import { describe, expect, it } from "vitest";

import { render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

const worksheetInput = {
  title: "Equivalent Fractions Worksheet",
  subject: "Math",
  gradeLevel: "Grade 5",
  sections: [
    {
      title: "Visual Models",
      instructions: "Show your thinking.",
      questions: [
        { id: "w1", prompt: "Draw 1/2 and 2/4.", type: "short_answer", answer: "same shaded amount", explanation: "Both cover half." },
        { id: "w-secret", prompt: "Teacher note", type: "short_answer", answer: "SECRET_WORKSHEET", teacher_only: true },
      ],
    },
  ],
} as const;

const drillInput = {
  title: "Equivalent Fractions Drill",
  subject: "Math",
  gradeLevel: "Grade 5",
  timeLimit: 8,
  questions: [
    { id: "d1", prompt: "Fill in: 1/2 = __/4", answer: "2", explanation: "Multiply by 2.", type: "fill" },
    { id: "d2", prompt: "Choose an equivalent fraction.", answer: "A", type: "mc", options: [{ label: "A", text: "4/6" }, { label: "B", text: "3/5" }] },
    { id: "d-secret", prompt: "Teacher-only", answer: "SECRET_DRILL", type: "fill", teacher_only: true },
  ],
} as const;

function context(kind: "worksheet" | "drill", renderMode: RenderContext["renderMode"]): RenderContext {
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

describe("practice artifact plugins", () => {
  it("declares worksheet and drill registry metadata", () => {
    const metadata = rendererPluginMetadata();

    expect(metadata).toContainEqual({
      kind: "worksheet",
      version: "0.1.0",
      templateVersion: "worksheet-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "worksheet-policy-v1",
    });
    expect(metadata).toContainEqual({
      kind: "drill",
      version: "0.1.0",
      templateVersion: "drill-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "drill-policy-v1",
    });
  });

  it("renders worksheet standalone HTML without answer or teacher-only leakage", async () => {
    const response = await render({ kind: "worksheet", input: worksheetInput, context: context("worksheet", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Equivalent Fractions Worksheet");
    expect(response.html).toContain("Draw 1/2 and 2/4");
    expect(response.html).not.toContain("same shaded amount");
    expect(response.html).not.toContain("SECRET_WORKSHEET");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("worksheet");
    expect(response.html).toMatchSnapshot("worksheet-student-preview");
  });

  it("renders drill standalone HTML without answer or teacher-only leakage", async () => {
    const response = await render({ kind: "drill", input: drillInput, context: context("drill", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Equivalent Fractions Drill");
    expect(response.html).toContain("Fill in: 1/2 = __/4");
    expect(response.html).toContain("Choose an equivalent fraction");
    expect(response.html).not.toContain("Multiply by 2");
    expect(response.html).not.toContain("SECRET_DRILL");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("drill");
    expect(response.html).toMatchSnapshot("drill-student-preview");
  });

  it("supports print mode for both practice plugins", async () => {
    const [worksheet, drill] = await Promise.all([
      render({ kind: "worksheet", input: worksheetInput, context: context("worksheet", "print") }),
      render({ kind: "drill", input: drillInput, context: context("drill", "print") }),
    ]);

    expect(worksheet.html).toContain("@media print");
    expect(drill.html).toContain("@media print");
  });

  it("rejects invalid practice inputs before rendering", async () => {
    await expect(render({ kind: "worksheet", input: { ...worksheetInput, sections: [] }, context: context("worksheet", "preview") })).rejects.toThrow(/validation failed/i);
    await expect(render({ kind: "drill", input: { ...drillInput, questions: [] }, context: context("drill", "preview") })).rejects.toThrow(/validation failed/i);
  });
});
