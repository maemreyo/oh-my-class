import { describe, expect, it } from "vitest";

import { renderAgentArtifact } from "../src/agent-renderer.js";

describe("renderAgentArtifact", () => {
  it("does not render explicit quiz answer fields in student HTML", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "quiz",
      title: "Animal Quiz",
      metadata: { subject: "English", grade_level: "Grade 3" },
      sections: [
        {
          id: "q1",
          content: "Which animal has a trunk?",
          options: { A: "Lion", B: "Elephant", C: "Dolphin", D: "Eagle" },
          correct_answer: "B",
          explanation: "Elephants use trunks to breathe, smell, drink, and grasp objects.",
        },
      ],
    });

    expect(html).not.toContain("Đáp án: B");
    expect(html).not.toContain("Elephants use trunks");
    expect(html).not.toContain("Đáp án: A");
  });

  it("does not invent a quiz answer when the agent artifact omits it", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "quiz",
      title: "Animal Quiz",
      metadata: { subject: "English", grade_level: "Grade 3" },
      sections: [
        {
          id: "q1",
          content: "Which animal has a trunk?",
          options: { A: "Lion", B: "Elephant", C: "Dolphin", D: "Eagle" },
        },
      ],
    });

    expect(html).not.toContain("Đáp án:");
  });

  it("renders question_card component from lesson section", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "English Vocabulary Lesson",
      metadata: { subject: "English", grade_level: "Grade 5" },
      sections: [
        {
          title: "Practice Questions",
          content: "Test your understanding",
          components: [
            {
              type: "question_card",
              id: 1,
              text: "Which word is a synonym for 'happy'?",
              options: { A: "Sad", B: "Joyful", C: "Angry", D: "Tired" },
              answer: "B",
              explain: "Joyful means feeling or expressing great pleasure.",
            },
          ],
        },
      ],
    });

    expect(html).toContain("Which word is a synonym for 'happy'?");
    expect(html).toContain("Joyful");
    expect(html).not.toContain("Giải thích");
    expect(html).not.toContain("Joyful means feeling or expressing great pleasure.");
  });

  it("does not render roleplay answer keys in lesson student HTML", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "Classroom Objects Lesson",
      metadata: { subject: "English", grade_level: "Grade 5" },
      sections: [
        {
          title: "Roleplay",
          content: "Practice asking for classroom objects.",
          components: [
            {
              type: "roleplay_script",
              lines: [
                { speaker: "A", text: "May I borrow a [blank_1]?" },
                { speaker: "B", text: "Here you are." },
              ],
              answer_key: ["pencil"],
            },
          ],
        },
      ],
    });

    expect(html).toContain("May I borrow a");
    expect(html).not.toContain("Đáp án");
    expect(html).not.toContain("pencil");
  });

  it("renders vocab_cluster component from lesson section", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "Vocabulary Builder",
      metadata: { subject: "English", grade_level: "Grade 4" },
      sections: [
        {
          title: "Animal Vocabulary",
          content: "Learn new words about animals",
          components: [
            {
              type: "vocab_cluster",
              title: "Farm Animals",
              description: "Common animals found on farms",
              items: [
                { word: "Cow", definition: "A large farm animal that gives milk" },
                { word: "Sheep", definition: "A woolly farm animal" },
              ],
            },
          ],
        },
      ],
    });

    expect(html).toContain("Farm Animals");
    expect(html).toContain("Common animals found on farms");
    expect(html).toContain("Cow");
    expect(html).toContain("A large farm animal that gives milk");
  });

  it("preserves backward compatibility with lessons without components", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      title: "Simple Lesson",
      metadata: { subject: "Math", grade_level: "Grade 3" },
      sections: [
        {
          title: "Introduction",
          content: "Basic math concepts",
        },
      ],
    });

    expect(html).toContain("Introduction");
    expect(html).toContain("Basic math concepts");
  });

  it("renders drill artifacts with the drill template", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "drill",
      title: "Food Drill",
      metadata: { subject: "English", grade_level: "Grade 5" },
      sections: [
        {
          id: "d1",
          content: "Choose the food word.",
          options: { A: "Apple", B: "Chair", C: "Pencil", D: "Window" },
          answer: "A",
        },
      ],
    });

    expect(html).toContain("drill-page");
    expect(html).toContain("Choose the food word.");
  });

  it("renders recap artifacts with recap cards", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "recap",
      title: "Food Recap",
      metadata: { subject: "English", grade_level: "Grade 5" },
      sections: [{ title: "Fruit", content: "Fruit words name sweet plant foods." }],
    });

    expect(html).toContain("recap-page");
    expect(html).toContain("Fruit words name sweet plant foods.");
  });

  it("renders infographic artifacts with infographic sections", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "infographic",
      title: "Food Infographic",
      metadata: { subject: "English", grade_level: "Grade 5" },
      sections: [{ title: "Food Groups", content: "Fruit, vegetables, grains, and protein." }],
    });

    expect(html).toContain("infographic-page");
    expect(html).toContain("Food Groups");
  });

  it("renders answer_key artifacts with the answer key template", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "answer_key",
      title: "Teacher Answers",
      metadata: { subject: "English", grade_level: "Grade 5" },
      sections: [{ id: "a1", title: "Quiz", content: "1. A" }],
    });

    expect(html).toContain("Teacher Answers");
    expect(html).toContain("oh-my-class");
  });

  it("renders a teaching_pack bundle combining every child artifact into one document (#453)", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "teaching_pack",
      title: "Fractions Unit",
      subject: "Math",
      gradeLevel: "Grade 5",
      children: [
        {
          id: "lesson-1",
          input: {
            artifact_type: "lesson",
            title: "Intro to Fractions",
            sections: [{ id: "s1", type: "objective", title: "Objective", content: "Understand fractions" }],
          },
        },
        {
          id: "quiz-1",
          input: {
            artifact_type: "quiz",
            title: "Fractions Quiz",
            sections: [{ id: "q1", content: "What is 1/2 + 1/2?", options: { A: "1", B: "2", C: "0" } }],
          },
        },
      ],
    });

    expect(html).toContain("Fractions Unit");
    expect(html).toContain("Intro to Fractions");
    expect(html).toContain("Fractions Quiz");
  });

  it("omits a teaching_pack child with no bundle-safe renderer instead of mis-rendering it as a lesson", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "teaching_pack",
      title: "Mixed Unit",
      subject: "Math",
      gradeLevel: "Grade 5",
      children: [
        {
          id: "lesson-1",
          input: {
            artifact_type: "lesson",
            title: "Intro to Fractions",
            sections: [{ id: "s1", type: "objective", title: "Objective", content: "Understand fractions" }],
          },
        },
        {
          id: "deck-1",
          input: {
            artifact_type: "slide_deck",
            title: "Fractions Deck",
            sections: [{ id: "sec1" }],
          },
        },
      ],
    });

    expect(html).toContain("Intro to Fractions");
    expect(html).not.toContain("Fractions Deck");
  });
});
