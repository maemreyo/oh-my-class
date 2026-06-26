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
});
