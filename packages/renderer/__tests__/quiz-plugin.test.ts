import { describe, expect, it } from "vitest";

import { render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

const quizInput = {
  title: "Equivalent Fractions Quiz",
  subject: "Math",
  gradeLevel: "Grade 5",
  timeLimit: 10,
  questions: [
    {
      id: "q1",
      prompt: "Which fraction equals 1/2?",
      options: [
        { label: "A", text: "1/4" },
        { label: "B", text: "2/4" },
      ],
      answer: "B",
      explain: "2/4 simplifies to 1/2.",
      timeMinutes: 2,
    },
  ],
} as const;

function context(audience: RenderContext["audience"], renderMode: RenderContext["renderMode"]): RenderContext {
  return {
    audience,
    locale: "en",
    theme: "default",
    renderMode,
    requestId: `quiz-${audience}-${renderMode}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("quiz plugin", () => {
  it("declares registry metadata", () => {
    expect(rendererPluginMetadata()).toContainEqual({
      kind: "quiz",
      version: "0.1.0",
      templateVersion: "quiz-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "quiz-policy-v1",
    });
  });

  it("renders student standalone HTML without answer or explanation leakage", async () => {
    const response = await render({ kind: "quiz", input: quizInput, context: context("student", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Equivalent Fractions Quiz");
    expect(response.html).toContain("Which fraction equals 1/2?");
    expect(response.html).toContain("oh-my-class");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.html).not.toContain('aria-checked="true"');
    expect(response.html).not.toContain("2/4 simplifies to 1/2");
    expect(response.manifest.kind).toBe("quiz");
    expect(response.diagnostics).toEqual([]);
    expect(response.metrics.renderTimeMs).toBeGreaterThanOrEqual(0);
  });

  it("renders teacher output with answer reveal data", async () => {
    const response = await render({ kind: "quiz", input: quizInput, context: context("teacher", "preview") });

    expect(response.html).toContain('aria-checked="true"');
    expect(response.html).toContain("2/4 simplifies to 1/2");
  });

  it("supports preview export and print render modes", async () => {
    const responses = await Promise.all([
      render({ kind: "quiz", input: quizInput, context: context("student", "preview") }),
      render({ kind: "quiz", input: quizInput, context: context("student", "export") }),
      render({ kind: "quiz", input: quizInput, context: context("student", "print") }),
    ]);

    for (const response of responses) {
      expect(response.html).toContain("@media print");
      expect(response.manifest.kind).toBe("quiz");
    }
  });

  it("rejects invalid quiz input before rendering", async () => {
    await expect(
      render({ kind: "quiz", input: { ...quizInput, questions: [] }, context: context("student", "preview") }),
    ).rejects.toThrow(/validation failed/i);
  });
});
