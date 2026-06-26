import { describe, expect, it } from "vitest";

import { renderAgentArtifact } from "../src/agent-renderer.js";

describe("renderAgentArtifact", () => {
  it("uses explicit quiz answer fields instead of falling back to A", async () => {
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

    expect(html).toContain("Đáp án: B");
    expect(html).toContain("Elephants use trunks");
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
    expect(html).toContain("Giải thích");
    expect(html).toContain("Joyful means feeling or expressing great pleasure.");
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
});
