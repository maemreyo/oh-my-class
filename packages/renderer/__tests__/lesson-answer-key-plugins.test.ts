import { describe, expect, it } from "vitest";

import { RendererErrorCode, render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

const lessonInput = {
  title: "Equivalent Fractions Lesson",
  subject: "Math",
  gradeLevel: "Grade 5",
  objectives: ["Explain why two fractions can represent the same amount."],
  sections: [
    {
      heading: "Launch",
      body: "Compare two shaded bars.",
      id: "launch",
      components: [
        {
          type: "question_card",
          id: "q1",
          text: "Which fraction is equivalent to 1/2?",
          options: { A: "2/4", B: "3/5" },
          answer: "A",
          explain: "2/4 simplifies to 1/2.",
          wrong_reasons: { B: "3/5 is not one half." },
        },
        {
          type: "active_recall_prompt",
          instruction: "State the rule in your own words.",
          reveal_answer: "Multiply numerator and denominator by the same number.",
          teacher_rationale: "Checks multiplicative reasoning.",
        },
      ],
    },
    {
      heading: "Teacher Notes",
      body: "SECRET_LESSON_SECTION",
      teacher_only: true,
    },
  ],
  vocabulary: [{ term: "Equivalent", definition: "Equal in value." }],
} as const;

const answerKeyInput = {
  title: "Equivalent Fractions Answer Key",
  sections: [
    {
      id: "answers",
      title: "Quiz Answers",
      summary: "Use this after students finish.",
      components: [
        {
          type: "question_card",
          id: "q1",
          text: "Which fraction is equivalent to 1/2?",
          options: { A: "2/4", B: "3/5" },
          answer: "A",
          explain: "2/4 simplifies to 1/2.",
        },
      ],
    },
  ],
  metadata: { total_questions: 1 },
  accessibility: { language: "en" },
} as const;

function context(kind: "lesson" | "answer_key", audience: RenderContext["audience"], renderMode: RenderContext["renderMode"]): RenderContext {
  return {
    audience,
    locale: "en",
    theme: "default",
    renderMode,
    requestId: `${kind}-${audience}-${renderMode}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("lesson and answer key plugins", () => {
  it("declares lesson and answer_key registry metadata", () => {
    const metadata = rendererPluginMetadata();

    expect(metadata).toContainEqual({
      kind: "lesson",
      version: "0.1.0",
      templateVersion: "lesson-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher", "student"],
      supportsPrint: true,
      sanitizerPolicyVersion: "lesson-policy-v1",
    });
    expect(metadata).toContainEqual({
      kind: "answer_key",
      version: "0.1.0",
      templateVersion: "answer-key-template-v1",
      themeVersion: "theme-resolver-v1",
      supportedAudiences: ["teacher"],
      supportsPrint: true,
      sanitizerPolicyVersion: "answer-key-policy-v1",
    });
  });

  it("renders student lesson without answer, explanation, or teacher-only leakage", async () => {
    const response = await render({ kind: "lesson", input: lessonInput, context: context("lesson", "student", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Equivalent Fractions Lesson");
    expect(response.html).toContain("Which fraction is equivalent to 1/2?");
    expect(response.html).not.toContain("2/4 simplifies to 1/2");
    expect(response.html).not.toContain("Multiply numerator and denominator");
    expect(response.html).not.toContain("SECRET_LESSON_SECTION");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("lesson");
    expect(response.html).toMatchSnapshot("lesson-student-preview");
  });

  it("renders answer_key only for teacher audience", async () => {
    const response = await render({ kind: "answer_key", input: answerKeyInput, context: context("answer_key", "teacher", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Equivalent Fractions Answer Key");
    expect(response.html).toContain("2/4 simplifies to 1/2");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("answer_key");
    expect(response.html).toMatchSnapshot("answer-key-teacher-preview");
  });

  it("rejects answer_key rendering for student audience", async () => {
    await expect(render({ kind: "answer_key", input: answerKeyInput, context: context("answer_key", "student", "preview") })).rejects.toMatchObject({
      code: RendererErrorCode.UnsupportedAudience,
    });
  });

  it("supports print mode for lesson and answer_key", async () => {
    const [lesson, answerKey] = await Promise.all([
      render({ kind: "lesson", input: lessonInput, context: context("lesson", "student", "print") }),
      render({ kind: "answer_key", input: answerKeyInput, context: context("answer_key", "teacher", "print") }),
    ]);

    expect(lesson.html).toContain("@media print");
    expect(answerKey.html).toContain("@media print");
  });
});
