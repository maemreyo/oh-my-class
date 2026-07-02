import { describe, expect, it } from "vitest";

import { RendererErrorCode, render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

const lessonInput = {
  title: "Bundle Lesson",
  subject: "Math",
  gradeLevel: "Grade 5",
  objectives: ["Explain equivalent fractions."],
  sections: [{ heading: "Launch", body: "Compare 1/2 and 2/4." }],
} as const;

const worksheetInput = {
  title: "Bundle Worksheet",
  subject: "Math",
  gradeLevel: "Grade 5",
  sections: [{ title: "Practice", questions: [{ id: "w1", prompt: "Draw 1/2.", type: "short_answer" }] }],
} as const;

const teachingPackInput = {
  title: "Equivalent Fractions Pack",
  subject: "Math",
  gradeLevel: "Grade 5",
  children: [
    { id: "lesson-child", kind: "lesson", input: lessonInput },
    { id: "worksheet-child", kind: "worksheet", input: worksheetInput },
  ],
} as const;

function context(renderMode: RenderContext["renderMode"]): RenderContext {
  return {
    audience: "student",
    locale: "en",
    theme: "default",
    renderMode,
    requestId: `teaching-pack-${renderMode}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("teaching_pack bundle plugin", () => {
  it("declares registry metadata", () => {
    expect(rendererPluginMetadata()).toContainEqual({
      kind: "teaching_pack",
      version: "0.1.0",
      templateVersion: "teaching-pack-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "teaching-pack-policy-v1",
    });
  });

  it("renders children through the registry and exposes child manifests", async () => {
    const response = await render({ kind: "teaching_pack", input: teachingPackInput, context: context("preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Equivalent Fractions Pack");
    expect(response.html).toContain("Bundle Lesson");
    expect(response.html).toContain("Bundle Worksheet");
    expect(response.html).toContain("Child manifests");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("teaching_pack");
    expect(response.manifest.childManifests?.map((manifest) => manifest.kind)).toEqual(["lesson", "worksheet"]);
    expect(response.html).toContain('class="teaching-pack-bundle"');
    expect(response.html).toContain('data-child-kind="lesson"');
    expect(response.html).toContain('data-child-kind="worksheet"');
    expect(response.html).toContain('"kind": "lesson"');
    expect(response.html).toContain('"kind": "worksheet"');
  });

  it("supports print mode for the bundle", async () => {
    const response = await render({ kind: "teaching_pack", input: teachingPackInput, context: context("print") });

    expect(response.html).toContain("@media print");
    expect(response.manifest.childManifests).toHaveLength(2);
  });

  it("rejects malformed child artifacts fail-closed", async () => {
    await expect(render({
      kind: "teaching_pack",
      input: {
        ...teachingPackInput,
        children: [{ id: "bad-child", kind: "worksheet", input: { ...worksheetInput, sections: [] } }],
      },
      context: context("preview"),
    })).rejects.toMatchObject({ code: RendererErrorCode.ValidationFailed });
  });

  it("rejects malformed bundle input before rendering children", async () => {
    await expect(render({ kind: "teaching_pack", input: { ...teachingPackInput, children: [] }, context: context("preview") })).rejects.toThrow(/validation failed/i);
    await expect(render({ kind: "teaching_pack", input: { ...teachingPackInput, children: [{ kind: "teaching_pack", input: teachingPackInput }] }, context: context("preview") })).rejects.toThrow(/validation failed/i);
  });
});
