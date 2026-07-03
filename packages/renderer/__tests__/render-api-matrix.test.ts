import { describe, expect, it } from "vitest";

import { render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

// ── Matrix cases — one entry per registered non-specialty plugin ─────────────

const MATRIX_CASES = [
  {
    kind: "quiz",
    audience: "student" as const,
    input: {
      title: "Matrix Quiz", subject: "English", gradeLevel: "Grade 5", timeLimit: 10,
      questions: [{ id: "q1", prompt: "Choose the synonym for 'happy'.", options: [{ label: "A", text: "Sad" }, { label: "B", text: "Joyful" }], answer: "SECRET_MATRIX_ANSWER", explain: "SECRET_MATRIX_EXPLAIN" }],
    },
  },
  {
    kind: "worksheet",
    audience: "student" as const,
    input: {
      title: "Matrix Worksheet", subject: "English", gradeLevel: "Grade 5",
      sections: [{ title: "Practice", questions: [{ id: "w1", prompt: "Write a sentence.", type: "short_answer" }] }],
    },
  },
  {
    kind: "drill",
    audience: "student" as const,
    input: {
      title: "Matrix Drill", subject: "English", gradeLevel: "Grade 5", timeLimit: 5,
      questions: [{ id: "d1", prompt: "Fill the blank: I ___ happy.", answer: "SECRET_DRILL_ANSWER", type: "fill" as const }],
    },
  },
  {
    kind: "recap",
    audience: "student" as const,
    input: {
      title: "Matrix Recap", subject: "English", gradeLevel: "Grade 5",
      items: [{ id: "r1", concept: "Synonyms", summary: "Words with similar meaning." }],
    },
  },
  {
    kind: "infographic",
    audience: "student" as const,
    input: {
      title: "Matrix Infographic", subject: "English", gradeLevel: "Grade 5",
      sections: [{ title: "Word Families", content: "Happy, joyful, elated are synonyms." }],
    },
  },
  {
    kind: "lesson",
    audience: "student" as const,
    input: {
      title: "Matrix Lesson", subject: "English", gradeLevel: "Grade 5", objectives: [],
      sections: [{ heading: "Introduction", body: "Today we learn synonyms." }],
    },
  },
  {
    kind: "answer_key",
    audience: "teacher" as const, // answer_key only supports teacher
    input: {
      title: "Matrix Answer Key",
      sections: [{ id: "ak1", title: "Quiz Answers", summary: "See answers below.", components: [] }],
      metadata: { total_questions: 1 },
      accessibility: { language: "en" },
    },
  },
  {
    kind: "flashcard_deck",
    audience: "student" as const,
    input: {
      title: "Matrix Flashcards", subject: "English", gradeLevel: "Grade 5",
      cards: [{ id: "fc1", front: "happy", back: "joyful" }],
    },
  },
  {
    kind: "reading_passage",
    audience: "student" as const,
    input: {
      title: "Matrix Reading", subject: "English", gradeLevel: "Grade 5",
      passage: "The quick brown fox jumps over the lazy dog.",
      questions: [{ id: "rp1", prompt: "What did the fox jump over?", answer: "SECRET_RP_ANSWER", type: "short_answer" as const }],
    },
  },
  {
    kind: "exit_ticket",
    audience: "student" as const,
    input: {
      title: "Matrix Exit Ticket", subject: "English", gradeLevel: "Grade 5",
      questions: [{ id: "et1", prompt: "Rate your confidence today.", type: "rating" as const }],
    },
  },
  {
    kind: "roadmap",
    audience: "student" as const,
    input: {
      title: "Matrix Roadmap",
      hero: { title: "Learning Roadmap", lede: "Your path to mastery." },
      sidebar: { title: "Navigation", subtitle: "Jump to sections." },
    },
  },
  {
    kind: "teaching_pack",
    audience: "teacher" as const,
    input: {
      title: "Matrix Teaching Pack", subject: "English", gradeLevel: "Grade 5",
      children: [{
        id: "child-quiz",
        kind: "quiz",
        input: {
          title: "Pack Quiz", subject: "English", gradeLevel: "Grade 5", timeLimit: 5,
          questions: [{ id: "pq1", prompt: "Choose a synonym.", options: [{ label: "A", text: "Sad" }, { label: "B", text: "Joyful" }], answer: "B" }],
        },
      }],
    },
  },
] as const;

// Kinds covered by this matrix
const MATRIX_KINDS = new Set(MATRIX_CASES.map((c) => c.kind));

// Specialty kinds that are validated in their own dedicated test files
const SPECIALTY_KINDS = new Set([
  "navy-ticket.teaching",
  "navy-ticket.practice",
  "investigation-folder.inverse-thinking",
  "paper-dossier.root-cause-session",
  "transit-route.video-route",
]);

function makeContext(kind: string, audience: RenderContext["audience"]): RenderContext {
  return {
    audience,
    locale: "vi",
    theme: "default",
    renderMode: "preview",
    requestId: `matrix-${kind}`,
    versions: { rendererVersion: "test-v1" },
    assetPolicy: "inline-only",
  };
}

// ── 1. Parametric matrix: each kind × audience renders valid standalone HTML ──

describe("render() API matrix — all 12 registered artifact plugins", () => {
  for (const { kind, audience, input } of MATRIX_CASES) {
    it(`renders ${kind} for ${audience} audience`, async () => {
      const response = await render(
        { kind, input, context: makeContext(kind, audience) },
      );

      expect(response.html).toMatch(/^<!DOCTYPE html>/i);
      expect(response.html).toContain("<html");
      expect(response.html).not.toMatch(/https?:\/\//);

      expect(response.manifest.kind).toBe(kind);
      expect(response.manifest.locale).toBe("vi");
      expect(response.manifest.audience).toBe(audience);
      expect(typeof response.manifest.contentHash).toBe("string");
      expect(response.manifest.contentHash.length).toBeGreaterThan(0);
    });
  }
});

// ── 2. Student safety: no SECRET sentinel values leak into student output ──────

describe("render() API matrix — student output does not expose SECRET sentinel values", () => {
  for (const { kind, audience, input } of MATRIX_CASES) {
    if (audience !== "student") continue;

    it(`${kind} student output does not expose SECRET sentinel values`, async () => {
      const response = await render(
        { kind, input, context: makeContext(kind, audience) },
      );
      const html = response.html;

      // Check the sentinels that are actually present in this kind's input
      if (kind === "quiz") {
        expect(html).not.toContain("SECRET_MATRIX_ANSWER");
        expect(html).not.toContain("SECRET_MATRIX_EXPLAIN");
      }
      if (kind === "drill") {
        expect(html).not.toContain("SECRET_DRILL_ANSWER");
      }
      if (kind === "reading_passage") {
        expect(html).not.toContain("SECRET_RP_ANSWER");
      }
    });
  }
});

// ── 3. Registry coverage: matrix covers all non-fixture, non-specialty plugins ─

describe("render() API matrix — registry coverage", () => {
  it("render-api-matrix covers all registered non-fixture plugins", () => {
    const allKinds = rendererPluginMetadata()
      .filter((plugin) => !plugin.kind.startsWith("fixture."))
      .map((plugin) => plugin.kind);

    const uncovered = allKinds.filter(
      (kind) => !MATRIX_KINDS.has(kind) && !SPECIALTY_KINDS.has(kind),
    );

    expect(uncovered).toEqual([]);
  });
});
