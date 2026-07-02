import { describe, expect, it } from "vitest";

import {
  render,
  rendererPluginMetadata,
  sanitizeRenderedHtml,
} from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

// ── helpers ──────────────────────────────────────────────────────────────────

function ctx(audience: "teacher" | "student", renderMode = "preview" as const): RenderContext {
  return {
    audience,
    locale: "vi",
    theme: "default",
    renderMode,
    requestId: `qg-${audience}`,
    versions: { rendererVersion: "test-v1" },
    assetPolicy: "inline-only",
  };
}

// ── fixtures ──────────────────────────────────────────────────────────────────

const quizMinimal = {
  title: "T",
  subject: "S",
  gradeLevel: "G",
  timeLimit: 5,
  questions: [
    {
      id: "q1",
      prompt: "P?",
      options: [{ label: "A", text: "opt" }],
      answer: "A",
    },
  ],
};

const lessonWithTeacherContent = {
  title: "T",
  subject: "S",
  gradeLevel: "G",
  objectives: [],
  sections: [
    {
      heading: "S1",
      body: "body",
      id: "s1",
      components: [
        {
          type: "question_card",
          id: "q1",
          text: "Q?",
          options: { A: "a", B: "b" },
          answer: "A",
          explain: "TEACHER_EXPLAIN_SENTINEL",
          wrong_reasons: { B: "TEACHER_WRONG_SENTINEL" },
        },
      ],
    },
  ],
};

const lessonWithTeacherOnlySection = {
  title: "T",
  subject: "S",
  gradeLevel: "G",
  objectives: [],
  sections: [
    {
      heading: "Public Section",
      body: "visible body",
      id: "public",
    },
    {
      heading: "Teacher Notes",
      body: "TEACHER_ONLY_SENTINEL",
      id: "teacher-notes",
      teacher_only: true,
    },
  ],
};

// ── registry completeness ─────────────────────────────────────────────────────

describe("registry completeness", () => {
  it("all required artifact kinds are registered", () => {
    const metadata = rendererPluginMetadata();
    const kinds = metadata.map((m) => m.kind);

    const required = [
      "quiz",
      "worksheet",
      "drill",
      "recap",
      "infographic",
      "lesson",
      "answer_key",
      "flashcard_deck",
      "reading_passage",
      "exit_ticket",
      "roadmap",
      "teaching_pack",
    ];

    for (const kind of required) {
      expect(kinds, `expected kind "${kind}" to be registered`).toContain(kind);
    }
  });

  it("all required Artifact UI kinds are registered", () => {
    const metadata = rendererPluginMetadata();
    const kinds = metadata.map((m) => m.kind);

    const artifactUiKinds = [
      "investigation-folder.inverse-thinking",
      "paper-dossier.root-cause-session",
      "transit-route.video-route",
    ];

    for (const kind of artifactUiKinds) {
      expect(kinds, `expected Artifact UI kind "${kind}" to be registered`).toContain(kind);
    }
  });

  it("registry metadata has required fields for all plugins", () => {
    const metadata = rendererPluginMetadata();

    for (const plugin of metadata) {
      expect(plugin.kind, `plugin.kind should be a non-empty string`).toBeTypeOf("string");
      expect(plugin.kind.length, `plugin.kind should be non-empty`).toBeGreaterThan(0);

      expect(plugin.version, `plugin[${plugin.kind}].version should be a non-empty string`).toBeTypeOf("string");
      expect(plugin.version.length, `plugin[${plugin.kind}].version should be non-empty`).toBeGreaterThan(0);

      expect(plugin.sanitizerPolicyVersion, `plugin[${plugin.kind}].sanitizerPolicyVersion should be a non-empty string`).toBeTypeOf("string");
      expect(plugin.sanitizerPolicyVersion.length, `plugin[${plugin.kind}].sanitizerPolicyVersion should be non-empty`).toBeGreaterThan(0);
    }
  });
});

// ── teacher-content leak prevention ──────────────────────────────────────────

describe("teacher-content leak prevention", () => {
  it("student lesson does not expose question answer or explanation", async () => {
    const response = await render(
      { kind: "lesson", input: lessonWithTeacherContent, context: ctx("student") },
    );

    expect(response.html).not.toContain("TEACHER_EXPLAIN_SENTINEL");
    expect(response.html).not.toContain("TEACHER_WRONG_SENTINEL");
  });

  it("student lesson section marked teacher_only is excluded", async () => {
    const response = await render(
      { kind: "lesson", input: lessonWithTeacherOnlySection, context: ctx("student") },
    );

    expect(response.html).not.toContain("TEACHER_ONLY_SENTINEL");
  });
});

// ── sanitizer XSS corpus ──────────────────────────────────────────────────────

describe("sanitizer XSS corpus", () => {
  it("base sanitizer strips script tags", () => {
    const result = sanitizeRenderedHtml("<script>alert(1)</script>", { version: "v1" });
    expect(result).not.toContain("<script>");
  });

  it("base sanitizer strips javascript: href", () => {
    const result = sanitizeRenderedHtml('<a href="javascript:alert(1)">click</a>', { version: "v1" });
    expect(result).not.toContain("javascript:");
  });

  it("base sanitizer strips onerror attributes", () => {
    const result = sanitizeRenderedHtml("<img src=x onerror=alert(1)>", { version: "v1" });
    expect(result).not.toContain("onerror");
  });

  it("base sanitizer strips iframe", () => {
    const result = sanitizeRenderedHtml('<iframe src="javascript:alert(1)"></iframe>', { version: "v1" });
    expect(result).not.toContain("<iframe");
  });

  it("quiz sanitizer strips script tags from rendered content", () => {
    const result = sanitizeRenderedHtml(
      "<div><p>OK</p><script>evil()</script></div>",
      { version: "quiz-policy-v1", config: "quiz" },
    );
    expect(result).not.toContain("<script>");
    expect(result).toContain("OK");
  });

  it("lesson sanitizer strips onerror and script from full document", () => {
    const doc = `<!DOCTYPE html><html><body><p onclick="xss()">text</p><script>steal()</script></body></html>`;
    const result = sanitizeRenderedHtml(doc, { version: "lesson-policy-v1", config: "lesson" });
    expect(result).not.toContain("onclick");
    expect(result).not.toContain("<script>");
  });

  it("svg onload payload is stripped by base sanitizer", () => {
    const result = sanitizeRenderedHtml("<svg onload=alert(1)>", { version: "v1" });
    expect(result).not.toContain("onload");
  });
});

// ── quality gate: all plugins produce valid standalone HTML ───────────────────

describe("quality gate: all plugins produce valid standalone HTML", () => {
  it("quiz renders a valid standalone HTML document for student audience", async () => {
    const response = await render(
      { kind: "quiz", input: quizMinimal, context: ctx("student") },
    );

    const { html } = response;

    expect(html.trimStart()).toMatch(/^<!DOCTYPE html>/i);
    expect(html).toContain("<html");
    expect(html).not.toMatch(/https?:\/\//);
  });
});
