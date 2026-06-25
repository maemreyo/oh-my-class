import { describe, expect, it } from "vitest";
import { renderArtifact, renderArtifactSync, renderTemplate } from "../src/renderer.js";
import { sanitizeHtml } from "../src/sanitizer.js";
import { inlineCss, validateNoExternalUrls } from "../src/inline-assets.js";
import type { ArtifactType, ArtifactDataMap } from "../src/contracts/index.js";
// Note: minimalData type is augmented below to include roadmap

// ── Minimal data for each artifact type (smoke tests) ───────────────────────

const minimalData: ArtifactDataMap & { roadmap: ArtifactDataMap["roadmap"] } = {
  lesson: {
    title: "Test Lesson",
    subject: "Math",
    gradeLevel: "Grade 5",
    objectives: ["Objective 1"],
    sections: [{ heading: "Intro", body: "Hello" }],
  },
  quiz: {
    title: "Test Quiz",
    subject: "English",
    gradeLevel: "Grade 8",
    questions: [
      {
        id: "q1",
        prompt: "What is 2 + 2?",
        options: [
          { label: "A", text: "3" },
          { label: "B", text: "4" },
        ],
        answer: "B",
      },
    ],
  },
  drill: {
    title: "Test Drill",
    subject: "Math",
    gradeLevel: "Grade 5",
    questions: [
      { id: "d1", prompt: "3 × 4 = ?", answer: "12", type: "mc", options: [{ label: "A", text: "11" }, { label: "B", text: "12" }] },
    ],
  },
  worksheet: {
    title: "Test Worksheet",
    subject: "Science",
    gradeLevel: "Grade 6",
    sections: [{ title: "Part A", questions: [{ id: "w1", prompt: "Describe water", type: "short_answer" }] }],
  },
  recap: {
    title: "Test Recap",
    subject: "History",
    gradeLevel: "Grade 7",
    items: [{ id: "r1", concept: "Revolution", summary: "A major change" }],
  },
  infographic: {
    title: "Test Infographic",
    subject: "Geography",
    gradeLevel: "Grade 5",
    sections: [{ title: "Climate", content: "Tropical zone" }],
  },
  answer_key: {
    title: "Test Answer Key",
    sections: [
      {
        id: "s1",
        title: "Section 1",
        group: "a",
        components: [
          {
            type: "question_card",
            id: "ak1",
            text: "5 + 3 = ?",
            options: { A: "7", B: "8" },
            answer: "B",
            explain: "5 + 3 = 8",
          },
        ],
      },
    ],
  },
  flashcard_deck: {
    title: "Test Flashcards",
    subject: "English",
    gradeLevel: "Grade 6",
    cards: [{ id: "fc1", front: "Hello", back: "Xin chào" }],
  },
  reading_passage: {
    title: "Test Reading",
    subject: "English",
    gradeLevel: "Grade 7",
    passage: "The quick brown fox jumps over the lazy dog.",
    questions: [
      {
        id: "rp1",
        prompt: "What color is the fox?",
        answer: "brown",
        type: "short_answer",
      },
    ],
  },
  exit_ticket: {
    title: "Test Exit Ticket",
    subject: "Math",
    gradeLevel: "Grade 5",
    questions: [
      { id: "et1", prompt: "What did you learn today?", type: "short_answer" },
    ],
  },
  roadmap: {
    title: "Test Roadmap",
    hero: { title: "Test Learning Roadmap", eyebrow: "Lộ trình học tập", stamp: "HSA 40+" },
    sidebar: { title: "Test Roadmap", subtitle: "6 tháng" },
    sections: [
      {
        id: "phase-1",
        title: "Phase 1: Foundation",
        components: [
          {
            type: "phase_timeline",
            phases: [
              { title: "Month 1", when: "Tháng 1", goal: "Build foundation", group: "a" },
            ],
          },
        ],
      },
    ],
  },
};

// ── renderArtifact (async, typed) ────────────────────────────────────────────

describe("renderArtifact (async, typed)", () => {
  it("returns a promise", () => {
    const result = renderArtifact("quiz", minimalData.quiz);
    expect(result).toBeInstanceOf(Promise);
  });

  it("produces valid HTML with DOCTYPE for quiz", async () => {
    const html = await renderArtifact("quiz", minimalData.quiz);
    expect(html).toContain("<!DOCTYPE html>");
  });

  it("includes oh-my-class brand string", async () => {
    const html = await renderArtifact("quiz", minimalData.quiz);
    expect(html).toContain("oh-my-class");
  });

  it("renders the artifact title", async () => {
    const html = await renderArtifact("quiz", minimalData.quiz);
    expect(html).toContain("Test Quiz");
  });

  it("has no external CDN links (INVARIANT-04)", async () => {
    const html = await renderArtifact("quiz", minimalData.quiz);
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("inlines theme CSS (no external link tags)", async () => {
    const html = await renderArtifact("quiz", minimalData.quiz);
    expect(html).toContain("<style>");
    expect(html).not.toMatch(/<link\s/);
  });

  it("renders correct lang attribute", async () => {
    const html = await renderArtifact("quiz", minimalData.quiz);
    expect(html).toContain('lang="vi"');
  });

  it("renders English lang when specified", async () => {
    const data = { ...minimalData.quiz, lang: "en" };
    const html = await renderArtifact("quiz", data);
    expect(html).toContain('lang="en"');
  });
});

// ── Smoke test: all 10 artifact types ────────────────────────────────────────

describe("all artifact types render without throwing", () => {
  const types: (ArtifactType | "roadmap")[] = [
    "lesson", "quiz", "drill", "worksheet", "recap", "infographic",
    "answer_key", "flashcard_deck", "reading_passage", "exit_ticket", "roadmap",
  ];

  for (const type of types) {
    it(`renders ${type} to valid HTML`, async () => {
      const html = await renderArtifact(type as ArtifactType, (minimalData as Record<string, unknown>)[type] as ArtifactDataMap[ArtifactType]);
      expect(html).toContain("<!DOCTYPE html>");
      expect(html).toContain("oh-my-class");
      expect(html).not.toMatch(/https?:\/\//);
    });
  }
});

// ── renderArtifactSync (legacy, backward compat) ─────────────────────────────

describe("renderArtifactSync (legacy)", () => {
  const mockArtifact = {
    artifact_type: "lesson",
    title: "Test Lesson",
    sections: [{ title: "Intro", content: "Some content" }],
    accessibility: { language: "en" },
  };

  it("produces valid HTML with DOCTYPE", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).toContain("<!DOCTYPE html>");
  });

  it("includes oh-my-class brand string", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).toContain("oh-my-class");
  });

  it("inlines theme CSS (no external link tags)", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).toContain("<style>");
    expect(html).not.toMatch(/<link\s/);
  });

  it("renders the artifact title", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).toContain("Test Lesson");
  });

  it("renders section content", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).toContain("Some content");
  });

  it("uses lang attribute from accessibility", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).toContain('lang="en"');
  });

  it("uses vi lang when accessibility.language is vi", () => {
    const artifact = { ...mockArtifact, accessibility: { language: "vi" } };
    const html = renderArtifactSync(artifact);
    expect(html).toContain('lang="vi"');
  });

  it("has no external CDN links", () => {
    const html = renderArtifactSync(mockArtifact);
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("strips injected script tags", () => {
    const maliciousArtifact = {
      ...mockArtifact,
      sections: [{ title: "Safe", content: "<script>alert(1)</script>" }],
    };
    const html = renderArtifactSync(maliciousArtifact);
    expect(html).not.toContain("<script>");
  });
});

// ── renderTemplate ───────────────────────────────────────────────────────────

describe("renderTemplate", () => {
  it("returns a string", () => {
    const result = renderTemplate("Hello <%= it.name %>", { name: "World" });
    expect(typeof result).toBe("string");
  });

  it("renders Eta template expressions", () => {
    const result = renderTemplate("Hello <%= it.name %>", { name: "World" });
    expect(result).toContain("World");
  });

  it("returns empty string for empty template", () => {
    const result = renderTemplate("", {});
    expect(result).toBe("");
  });

  it("renders static content unchanged", () => {
    const result = renderTemplate("Static text", {});
    expect(result).toBe("Static text");
  });
});

// ── sanitizeHtml ─────────────────────────────────────────────────────────────

describe("sanitizeHtml", () => {
  it("removes script blocks", () => {
    const html = '<div>Safe</div><script>alert("xss")</script>';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("<script>");
    expect(clean).toContain("Safe");
  });

  it("removes inline script with attributes", () => {
    const html = '<script type="text/javascript">evil()</script><p>ok</p>';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("<script");
    expect(clean).toContain("ok");
  });

  it("removes onclick event handlers", () => {
    const html = '<div onclick="alert(1)">Safe</div>';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("onclick");
    expect(clean).toContain("Safe");
  });

  it("removes onerror event handlers", () => {
    const html = '<img src="x" onerror="alert(1)">';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("onerror");
  });

  it("removes onload event handlers", () => {
    const html = '<body onload="steal()">content</body>';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("onload");
    expect(clean).toContain("content");
  });

  it("removes iframe tags", () => {
    const html = '<div>ok</div><iframe src="evil.com"></iframe>';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("iframe");
    expect(clean).toContain("ok");
  });

  it("removes embed tags", () => {
    const html = '<div>ok</div><embed src="evil.swf">';
    const clean = sanitizeHtml(html);
    expect(clean).not.toContain("embed");
  });

  it("preserves safe content", () => {
    const html = '<div class="content"><p>Hello</p></div>';
    const clean = sanitizeHtml(html);
    expect(clean).toContain("Hello");
    expect(clean).toContain('class="content"');
  });

  it("preserves style tags", () => {
    const html = "<style>body { color: red; }</style><p>text</p>";
    const clean = sanitizeHtml(html);
    expect(clean).toContain("<style>");
    expect(clean).toContain("color: red");
  });
});

// ── inlineCss / validateNoExternalUrls ───────────────────────────────────────

describe("inlineCss", () => {
  it("injects style tag before </head>", () => {
    const html = "<html><head></head><body>hi</body></html>";
    const result = inlineCss(html, "body { color: red; }");
    expect(result).toContain("<style>");
    expect(result).toContain("color: red");
    expect(result.indexOf("<style>")).toBeLessThan(result.indexOf("</head>"));
  });

  it("prepends style tag when no </head>", () => {
    const html = "<p>Hello</p>";
    const result = inlineCss(html, "p { margin: 0; }");
    expect(result).toContain("<style>");
    expect(result).toContain("Hello");
  });
});

describe("validateNoExternalUrls", () => {
  it("returns empty array for clean HTML", () => {
    const html = '<div class="ok"><p>Hello</p></div>';
    expect(validateNoExternalUrls(html)).toHaveLength(0);
  });

  it("detects external https URL in src", () => {
    const html = '<img src="https://cdn.example.com/image.png">';
    const violations = validateNoExternalUrls(html);
    expect(violations.length).toBeGreaterThan(0);
  });

  it("detects external http URL in href", () => {
    const html = '<link href="http://fonts.googleapis.com/css">';
    const violations = validateNoExternalUrls(html);
    expect(violations.length).toBeGreaterThan(0);
  });
});
