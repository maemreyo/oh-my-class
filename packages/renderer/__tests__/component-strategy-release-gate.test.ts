import { describe, expect, it } from "vitest";

import { renderAgentArtifact } from "../src/agent-renderer.js";

describe("Component Strategist renderer release gate", () => {
  it("renders v1 selected vocabulary components as standalone student HTML without teacher-only strategy metadata", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "lesson",
      theme: "default",
      title: "Strategy-selected vocabulary lesson",
      metadata: {
        subject: "English",
        grade_level: "Grade 5",
        component_strategy: {
          strategy_id: "strategy-cs08-vocabulary",
          slot_ids: ["slot-contrast", "slot-vocab"],
          audit_score_ledger: { overall: 1 },
        },
      },
      accessibility: { language: "en" },
      sections: [
        {
          id: "strategy-components",
          title: "Selected learning moves",
          content: "Compare confusable words before retrieval practice.",
          components: [
            {
              type: "contrastive_pairs",
              strategy_slot_id: "slot-contrast",
              title: "Trip vs journey",
              left_label: "Trip: purpose-bound visit",
              right_label: "Journey: longer process",
              rows: [
                {
                  terms: "trip / journey",
                  distinction: "Trip names a specific visit; journey emphasizes the process.",
                  example: "The class trip lasted one day.",
                  non_example: "The class journey lasted one day.",
                  boundary_note: "Use trip for short visits with a purpose.",
                  teacher_rationale: "TEACHER_ONLY_STRATEGY_RATIONALE",
                },
              ],
            },
            {
              type: "vocab_cluster",
              strategy_slot_id: "slot-vocab",
              title: "Travel word family",
              description: "Group meanings before practice.",
              items: [
                { word: "trip", definition: "A short visit for a purpose", example: "school trip" },
                { word: "journey", definition: "A longer movement or process", example: "a long journey" },
              ],
              discrimination_prompt: "Which word fits a short school visit?",
            },
          ],
        },
        {
          id: "teacher-notes",
          title: "Teacher notes",
          content: "TEACHER_ONLY_COMPONENT_STRATEGY_LEDGER",
          teacher_only: true,
        },
      ],
    });

    expect(html).toMatch(/^<!DOCTYPE html>/);
    expect(html).toContain("contrastive-pairs");
    expect(html).toContain("vocab-cluster");
    expect(html).toContain("Trip names a specific visit");
    expect(html).toContain("Travel word family");
    expect(html).not.toMatch(/https?:\/\//);
    expect(html).not.toContain("TEACHER_ONLY_STRATEGY_RATIONALE");
    expect(html).not.toContain("TEACHER_ONLY_COMPONENT_STRATEGY_LEDGER");
    expect(html).not.toContain("audit_score_ledger");
    expect(html).not.toContain("strategy_slot_id");
  });
});
