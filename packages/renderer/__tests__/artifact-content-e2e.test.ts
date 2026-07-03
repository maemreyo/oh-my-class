import { describe, expect, it } from "vitest";

import { renderAgentArtifact } from "../src/agent-renderer.js";

// ---------------------------------------------------------------------------
// Shared fixture — realistic ArtifactContent produced by the Content Creator
// ---------------------------------------------------------------------------

const realisticLesson = {
  artifact_type: "lesson",
  title: "Travel Vocabulary: Airport Actions",
  theme: "default",
  metadata: { subject: "English", grade_level: "Grade 8" },
  accessibility: { language: "en" },
  sections: [
    {
      title: "Warm-up",
      content: "Think about your last journey.",
      components: [
        {
          type: "film_clip_activity",
          clips: [{ title: "Airport scene", description: "Watch for travel verbs." }],
          hunt_chips: ["take off", "check in", "board"],
          post_viewing_note: "Which verb did you hear first?",
        },
      ],
    },
    {
      title: "Key Vocabulary",
      content: "Learn these airport action verbs.",
      components: [
        {
          type: "vocab_cluster",
          title: "Airport Verbs",
          description: "Actions at the airport",
          items: [
            { word: "check in", definition: "register for a flight at the counter", example: "We check in two hours before departure." },
            { word: "board", definition: "get onto a plane", example: "Passengers board after the gate opens." },
          ],
        },
      ],
    },
    {
      title: "Practice",
      content: "Test your understanding.",
      components: [
        {
          type: "question_card",
          id: "q1",
          text: "What does 'check in' mean at an airport?",
          options: { A: "Criticize someone", B: "Register for a flight", C: "Leave the airport", D: "Buy snacks" },
          answer: "B",
          explain: "SENTINEL_EXPLAIN",
          wrong_reasons: { A: "SENTINEL_WRONG_A" },
        },
        {
          type: "active_recall_prompt",
          instruction: "Without notes, recall two airport verbs.",
          reveal_answer: "SENTINEL_REVEAL",
          teacher_rationale: "SENTINEL_TEACHER_RAT",
          reflection_note: "How confident were you?",
        },
      ],
    },
    {
      title: "Teacher Notes",
      content: "SENTINEL_TEACHER_SECTION",
      teacher_only: true,
    },
  ],
};

// ---------------------------------------------------------------------------
// 1. Lesson E2E
// ---------------------------------------------------------------------------

describe("lesson E2E — realistic ArtifactContent", () => {
  it("renders standalone HTML with all required structure", async () => {
    const html = await renderAgentArtifact(realisticLesson);

    // Must be a complete standalone document
    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("oh-my-class");

    // Visible student content is present
    expect(html).toContain("What does 'check in' mean at an airport?");
    expect(html).toContain("Airport Verbs");

    // Teacher/answer fields are stripped from student output
    expect(html).not.toContain("SENTINEL_EXPLAIN");
    expect(html).not.toContain("SENTINEL_WRONG_A");
    expect(html).not.toContain("SENTINEL_TEACHER_SECTION");
    expect(html).not.toContain("SENTINEL_TEACHER_RAT");

    // active_recall_prompt reveal_answer is student-facing — must survive projection
    expect(html).toContain("SENTINEL_REVEAL");

    // No external URLs embedded
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("renders vocab_cluster component content", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "Vocabulary Lesson",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          title: "Word Study",
          content: "Study these words.",
          components: [
            {
              type: "vocab_cluster",
              title: "Transient Words",
              description: "Words about time",
              items: [
                { word: "ephemeral", definition: "lasting very short time", example: "The morning dew is ephemeral." },
              ],
            },
          ],
        },
      ],
    });

    expect(html).toContain("ephemeral");
    expect(html).toContain("lasting very short time");
  });

  it("renders film_clip_activity component", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "Film Activity Lesson",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          title: "Warm-up",
          content: "Watch and note the verbs.",
          components: [
            {
              type: "film_clip_activity",
              clips: [{ title: "Airport scene", description: "Watch for travel verbs." }],
              hunt_chips: ["take off", "land"],
              post_viewing_note: "Which verb did you hear?",
            },
          ],
        },
      ],
    });

    // At least one hunt chip must appear
    const containsChip = html.includes("take off") || html.includes("land");
    expect(containsChip).toBe(true);
  });

  it("renders active_recall_prompt with reveal button", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "Recall Lesson",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          title: "Retrieve",
          content: "Answer from memory.",
          components: [
            {
              type: "active_recall_prompt",
              instruction: "Name three airport action verbs.",
              reveal_answer: "check in, board, take off",
              teacher_rationale: "SENTINEL_TEACHER_RAT_RECALL",
              reflection_note: "How did you do?",
            },
          ],
        },
      ],
    });

    // Reveal button text or aria semantics must be present
    const hasReveal = html.includes("Show recall answer") || html.includes("aria-expanded");
    expect(hasReveal).toBe(true);
    expect(html).not.toContain("SENTINEL_TEACHER_RAT_RECALL");
  });
});

// ---------------------------------------------------------------------------
// 2. Quiz E2E — teacher content hidden
// ---------------------------------------------------------------------------

describe("quiz E2E — teacher content hidden", () => {
  it("does not expose answer or explanation in quiz HTML", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "quiz",
      title: "Travel Vocabulary Quiz",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          id: "q1",
          content: "Which phrase means to get on a plane?",
          options: { A: "Check out", B: "Land", C: "Board", D: "Depart" },
          correct_answer: "C",
          explanation: "SENTINEL_QUIZ_EXPLAIN",
        },
      ],
    });

    expect(html).not.toContain("SENTINEL_QUIZ_EXPLAIN");
    expect(html).not.toContain("Đáp án: C");
  });

  it("renders quiz question text and options", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "quiz",
      title: "Travel Vocabulary Quiz",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          id: "q2",
          content: "Which verb means to start a journey?",
          options: {
            A: "Arrive at a destination",
            B: "Set off on a trip",
            C: "Cancel a reservation",
            D: "Extend a layover",
          },
          correct_answer: "B",
        },
      ],
    });

    expect(html).toContain("Which verb means to start a journey?");
    expect(html).toContain("A");
    expect(html).toContain("B");
    expect(html).toContain("C");
    expect(html).toContain("D");
  });
});

// ---------------------------------------------------------------------------
// 3. Multi-type E2E smoke — all agent-supported artifact_types render without error
// ---------------------------------------------------------------------------

describe("multi-type E2E smoke — all agent-supported artifact_types render without error", () => {
  it("worksheet renders", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "worksheet",
      title: "Airport Actions Worksheet",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          title: "Fill in the blank",
          questions: [
            { id: "w1", prompt: "Passengers _____ at the gate before boarding.", type: "short_answer" },
            { id: "w2", prompt: "Write two airport verbs in a sentence.", type: "long_answer" },
          ],
        },
      ],
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("oh-my-class");
  });

  it("drill renders", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "drill",
      title: "Airport Verbs Drill",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          id: "d1",
          content: "Choose the verb that means to get on a plane.",
          options: { A: "board", B: "pack", C: "sleep", D: "read" },
          answer: "A",
        },
      ],
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("oh-my-class");
  });

  it("recap renders", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "recap",
      title: "Airport Actions Recap",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        { id: "r1", title: "Check in", content: "Register at the counter before your flight." },
        { id: "r2", title: "Board", content: "Get onto the plane after your gate opens." },
      ],
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("oh-my-class");
  });

  it("infographic renders", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "infographic",
      title: "Airport Verbs Infographic",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        { title: "Before the flight", content: "check in, pack, confirm" },
        { title: "At the gate", content: "board, take off, depart" },
      ],
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("oh-my-class");
  });

  it("answer_key renders (teacher view)", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "answer_key",
      title: "Airport Actions Answer Key",
      metadata: { subject: "English", grade_level: "Grade 8" },
      accessibility: { language: "en" },
      sections: [
        {
          id: "ak1",
          title: "Quiz Answers",
          content: "Q1: C — Board means to get onto a plane.",
          components: [
            {
              type: "question_card",
              id: "ak-q1",
              text: "Which verb means to get onto a plane?",
              options: { A: "Check out", B: "Land", C: "Board", D: "Depart" },
              answer: "C",
              explain: "Board specifically refers to entering the aircraft.",
            },
          ],
        },
      ],
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("oh-my-class");
  });
});

// ---------------------------------------------------------------------------
// 4. Cross-cutting safety invariants
// ---------------------------------------------------------------------------

describe("cross-cutting safety invariants", () => {
  it("no external URLs in any rendered artifact", async () => {
    const [lessonHtml, quizHtml, answerKeyHtml] = await Promise.all([
      renderAgentArtifact(realisticLesson),
      renderAgentArtifact({
        artifact_type: "quiz",
        title: "Travel Quiz",
        metadata: { subject: "English", grade_level: "Grade 8" },
        accessibility: { language: "en" },
        sections: [
          {
            id: "q1",
            content: "Which verb means to board a plane?",
            options: { A: "Check out", B: "Board", C: "Land", D: "Depart" },
            correct_answer: "B",
          },
        ],
      }),
      renderAgentArtifact({
        artifact_type: "answer_key",
        title: "Travel Answer Key",
        metadata: { subject: "English", grade_level: "Grade 8" },
        accessibility: { language: "en" },
        sections: [{ id: "ak1", title: "Answers", content: "Q1: B — Board." }],
      }),
    ]);

    expect(lessonHtml).not.toMatch(/https?:\/\//);
    expect(quizHtml).not.toMatch(/https?:\/\//);
    expect(answerKeyHtml).not.toMatch(/https?:\/\//);
  });

  it("all rendered artifacts are valid standalone HTML documents", async () => {
    const [lessonHtml, quizHtml, answerKeyHtml] = await Promise.all([
      renderAgentArtifact(realisticLesson),
      renderAgentArtifact({
        artifact_type: "quiz",
        title: "Travel Quiz",
        metadata: { subject: "English", grade_level: "Grade 8" },
        accessibility: { language: "en" },
        sections: [
          {
            id: "q1",
            content: "Which verb means to board a plane?",
            options: { A: "Check out", B: "Board", C: "Land", D: "Depart" },
            correct_answer: "B",
          },
        ],
      }),
      renderAgentArtifact({
        artifact_type: "answer_key",
        title: "Travel Answer Key",
        metadata: { subject: "English", grade_level: "Grade 8" },
        accessibility: { language: "en" },
        sections: [{ id: "ak1", title: "Answers", content: "Q1: B — Board." }],
      }),
    ]);

    for (const html of [lessonHtml, quizHtml, answerKeyHtml]) {
      expect(html).toContain("<!DOCTYPE html>");
      expect(html).toContain("<html");
      expect(html).toContain("<head");
      expect(html).toContain("<body");
    }
  });
});
