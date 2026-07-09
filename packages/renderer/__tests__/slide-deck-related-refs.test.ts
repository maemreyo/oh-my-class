import { describe, expect, it } from "vitest";

import { renderArtifact } from "../src/renderer.js";
import type { SlideDeckData } from "../src/contracts/index.js";

// SDTF-03 fixture: a slide/block pair that references a worksheet, a quiz,
// and an objective from the same run -- this stands in for real-LLM output
// without requiring a live LLM call. The worksheet/quiz are deliberately
// NOT present anywhere else in this fixture, standing in for "generated in
// this run" content that must never be copied into the deck.
const deckWithRelatedRefs: SlideDeckData = {
  deck_id: "deck-related-refs-test",
  title: "Fractions Practice Bridge",
  locale: "en-US",
  theme: "default",
  surfaces: {
    student: { mode: "presentation", export_format: "html" },
    teacher: { mode: "teacher_guide", export_format: "html" },
    print: { mode: "print", export_format: "html" },
  },
  slides: [
    {
      slide_id: "slide-practice",
      title: "Now Try It Yourself",
      layout: "activity",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      related_refs: [
        { artifact_type: "objective", artifact_id: "obj-fractions-1", relationship_label: "Builds on Objective 1" },
      ],
      blocks: [
        {
          block_id: "block-practice",
          block_type: "paragraph",
          body: "Work through the practice problems before the quiz.",
          related_refs: [
            {
              artifact_type: "worksheet",
              artifact_id: "worksheet-fractions-2",
              relationship_label: "See Worksheet 2",
            },
            {
              artifact_type: "quiz",
              artifact_id: "quiz-fractions-missing",
              relationship_label: "See the follow-up quiz",
            },
          ],
        },
      ],
      teacher_notes: {
        facilitation_notes: ["Point students to Worksheet 2 before the quiz check."],
        answer_key_notes: ["ANSWER_KEY_SECRET_2_4"],
      },
    },
  ],
  accessibility: {
    reading_level: "Grade 5",
    language: "en",
    alt_text_required: true,
    keyboard_navigation: true,
  },
  media_policy: {
    default_tier: "packaged",
    online_optional_allowed: true,
    fallback_required: true,
  },
};

describe("slide_deck related artifact references (SDTF-03)", () => {
  it("shows only the safe relationship label to students, never artifact_type/artifact_id or teacher notes", async () => {
    const html = await renderArtifact("slide_deck", deckWithRelatedRefs);

    expect(html).toContain("See Worksheet 2");
    expect(html).toContain("See the follow-up quiz");
    expect(html).toContain("Builds on Objective 1");

    // Pointer, not content: the internal join keys and teacher-only
    // planning context never reach student-facing HTML.
    expect(html).not.toContain("worksheet-fractions-2");
    expect(html).not.toContain("quiz-fractions-missing");
    expect(html).not.toContain("obj-fractions-1");
    expect(html).not.toContain("worksheet:");
    expect(html).not.toContain("quiz:");
    expect(html).not.toContain("objective:");
    expect(html).not.toContain("ANSWER_KEY_SECRET_2_4");
  });

  it("degrades gracefully when a referenced artifact was never generated in this run", async () => {
    // "quiz-fractions-missing" does not exist anywhere else in the fixture
    // (standing in for a sibling artifact that failed/was skipped this
    // run) -- standalone student export must still succeed.
    const html = await renderArtifact("slide_deck", deckWithRelatedRefs);

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("See the follow-up quiz");
  });

  it("shows teacher preview the artifact_type:artifact_id planning context alongside the label", async () => {
    const html = await renderArtifact("slide_deck", { ...deckWithRelatedRefs, render_surface: "teacher" });

    expect(html).toContain("See Worksheet 2");
    expect(html).toContain("worksheet:worksheet-fractions-2");
    expect(html).toContain("See the follow-up quiz");
    expect(html).toContain("quiz:quiz-fractions-missing");
    expect(html).toContain("Builds on Objective 1");
    expect(html).toContain("objective:obj-fractions-1");
  });

  it("exports standalone with no related_refs present at all (backward compatible)", async () => {
    const html = await renderArtifact("slide_deck", {
      ...deckWithRelatedRefs,
      slides: [{ ...deckWithRelatedRefs.slides[0], related_refs: undefined, blocks: [{ ...deckWithRelatedRefs.slides[0].blocks[0], related_refs: undefined }] }],
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).not.toContain("See Worksheet 2");
  });
});
