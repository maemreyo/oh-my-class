import { describe, expect, it } from "vitest";
import { renderArtifact } from "../src/renderer.js";

describe("template-library — quiz page", () => {
  it("renders question prompt", async () => {
    const html = await renderArtifact("quiz", {
      title: "Test Quiz",
      subject: "English",
      gradeLevel: "Grade 8",
      questions: [{
        id: "q1",
        prompt: "What is the capital of France?",
        options: [{ label: "A", text: "London" }, { label: "B", text: "Paris" }],
        answer: "B",
      }],
    });
    expect(html).toContain("What is the capital of France?");
    expect(html).toContain("London");
    expect(html).toContain("Paris");
  });

  it("renders question options as radio inputs", async () => {
    const html = await renderArtifact("quiz", {
      title: "Quiz",
      subject: "Science",
      gradeLevel: "Grade 5",
      questions: [{
        id: "q1",
        prompt: "2 + 2 = ?",
        options: [{ label: "A", text: "3" }, { label: "B", text: "4" }],
        answer: "B",
      }],
    });
    expect(html).toContain('type="radio"');
    expect(html).toContain('role="radiogroup"');
  });

  it("has no external URLs", async () => {
    const html = await renderArtifact("quiz", {
      title: "Quiz",
      subject: "Math",
      gradeLevel: "Grade 6",
      questions: [],
    });
    expect(html).not.toMatch(/https?:\/\//);
  });
});

describe("template-library — lesson page", () => {
  it("renders learning objectives", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      subject: "Math",
      gradeLevel: "Grade 5",
      objectives: ["Understand fractions", "Apply fractions"],
      sections: [],
    });
    expect(html).toContain("Understand fractions");
    expect(html).toContain("Apply fractions");
  });

  it("renders section content", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      subject: "Math",
      gradeLevel: "Grade 5",
      objectives: [],
      sections: [{ heading: "Introduction", body: "Welcome to math." }],
    });
    expect(html).toContain("Introduction");
    expect(html).toContain("Welcome to math.");
  });

  it("renders vocabulary section", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      subject: "English",
      gradeLevel: "Grade 7",
      objectives: [],
      sections: [],
      vocabulary: [{ term: "photosynthesis", definition: "Process by which plants make food" }],
    });
    expect(html).toContain("photosynthesis");
    expect(html).toContain("Process by which plants make food");
  });
});

describe("template-library — answer_key page", () => {
  it("shows all answers (no hide/reveal toggle)", async () => {
    const html = await renderArtifact("answer_key", {
      title: "Answer Key",
      sections: [{
        id: "s1",
        title: "Toán học",
        group: "a",
        components: [{
          type: "question_card",
          id: "ak1",
          text: "5 + 3 = ?",
          options: { A: "7", B: "8" },
          answer: "B",
          explain: "5 + 3 equals 8",
        }],
      }],
    });
    expect(html).toContain("5 + 3 = ?");
    expect(html).toContain("5 + 3 equals 8");
    expect(html).toContain("option correct");
  });

  it("renders answer key eyebrow and title", async () => {
    const html = await renderArtifact("answer_key", {
      title: "Answer Key",
      sections: [],
    });
    expect(html).toContain("Đáp án chi tiết");
    expect(html).toContain("Answer Key");
  });
});

describe("template-library — flashcard_deck page", () => {
  it("renders card fronts and backs", async () => {
    const html = await renderArtifact("flashcard_deck", {
      title: "Vocab Flashcards",
      subject: "English",
      gradeLevel: "Grade 6",
      cards: [{ id: "c1", front: "apple", back: "quả táo" }],
    });
    expect(html).toContain("apple");
    expect(html).toContain("quả táo");
  });

  it("includes navigation buttons", async () => {
    const html = await renderArtifact("flashcard_deck", {
      title: "Flashcards",
      subject: "English",
      gradeLevel: "Grade 6",
      cards: [
        { id: "c1", front: "cat", back: "mèo" },
        { id: "c2", front: "dog", back: "chó" },
      ],
    });
    expect(html).toContain("btn-prev");
    expect(html).toContain("btn-next");
  });
});

describe("template-library — exit_ticket page", () => {
  it("limits to 3 questions", async () => {
    const html = await renderArtifact("exit_ticket", {
      title: "Exit Ticket",
      subject: "Math",
      gradeLevel: "Grade 5",
      questions: [
        { id: "et1", prompt: "Q1?", type: "short_answer" },
        { id: "et2", prompt: "Q2?", type: "short_answer" },
        { id: "et3", prompt: "Q3?", type: "short_answer" },
        { id: "et4", prompt: "Q4 — should not appear", type: "short_answer" },
      ],
    });
    expect(html).toContain("Q1?");
    expect(html).toContain("Q3?");
    expect(html).not.toContain("Q4");
  });
});

describe("template-library — reading_passage page", () => {
  it("renders the passage text", async () => {
    const html = await renderArtifact("reading_passage", {
      title: "The Fox",
      subject: "English",
      gradeLevel: "Grade 7",
      passage: "The quick brown fox jumps over the lazy dog.",
      questions: [],
    });
    expect(html).toContain("The quick brown fox");
  });

  it("renders comprehension questions", async () => {
    const html = await renderArtifact("reading_passage", {
      title: "Reading",
      subject: "English",
      gradeLevel: "Grade 7",
      passage: "Some text here.",
      questions: [{
        id: "rq1",
        prompt: "What is the main idea?",
        answer: "test",
        type: "short_answer",
      }],
    });
    expect(html).toContain("What is the main idea?");
  });
});
