import { describe, expect, it } from "vitest";

import { renderArtifact } from "../src/renderer.js";
import type { SlideDeckData } from "../src/contracts/index.js";

// SDTF-05 fixture: teacher-only scaffold/stretch guidance, distinct from
// facilitation_notes/answer_key_notes -- standing in for real-LLM output
// without requiring a live LLM call.
const SCAFFOLD_LEAK_MARKER = "LEAK_SCAFFOLD_TIP data-answer=\"42\" <!-- LEAK_COMMENT --> <script>JSON.parse(\"LEAK_JSON\")</script>";
const STRETCH_LEAK_MARKER = "LEAK_STRETCH_TIP";

const deckWithDifferentiationGuidance: SlideDeckData = {
  deck_id: "deck-differentiation-guidance-test",
  title: "Equivalent Fractions Mini Deck",
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
      blocks: [
        { block_id: "block-practice", block_type: "paragraph", body: "Work through the practice problems." },
      ],
      teacher_notes: {
        facilitation_notes: ["Circulate while students work."],
        answer_key_notes: ["ANSWER_KEY_SECRET_2_4"],
      },
      differentiation_guidance: [
        { level: "scaffold", guidance: SCAFFOLD_LEAK_MARKER },
        { level: "stretch", guidance: STRETCH_LEAK_MARKER },
      ],
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

describe("slide_deck differentiation guidance (SDTF-05)", () => {
  it.each(["student", "presentation", "print"] as const)(
    "excludes scaffold/stretch guidance from %s HTML (no student leakage)",
    async (surface) => {
      const html = await renderArtifact("slide_deck", { ...deckWithDifferentiationGuidance, render_surface: surface });

      expect(html).not.toContain("LEAK_SCAFFOLD_TIP");
      expect(html).not.toContain(STRETCH_LEAK_MARKER);
      expect(html).not.toContain("differentiation_guidance");
      // Not just absent as bare text -- the answer-key sibling field must
      // also stay absent, proving this surface strips teacher-only content
      // generally, not just this one new field.
      expect(html).not.toContain("ANSWER_KEY_SECRET_2_4");
    },
  );

  it.each(["teacher", "review"] as const)(
    "surfaces scaffold and stretch guidance separately on the %s surface, distinct from the answer key",
    async (surface) => {
      const html = await renderArtifact("slide_deck", { ...deckWithDifferentiationGuidance, render_surface: surface });

      expect(html).toContain("LEAK_SCAFFOLD_TIP");
      expect(html).toContain(STRETCH_LEAK_MARKER);
      expect(html).toContain("Differentiation guidance");
      expect(html).toContain("scaffold");
      expect(html).toContain("stretch");
      expect(html).toContain("ANSWER_KEY_SECRET_2_4");
    },
  );

  it("exports standalone with no differentiation_guidance present at all (backward compatible)", async () => {
    const html = await renderArtifact("slide_deck", {
      ...deckWithDifferentiationGuidance,
      slides: [{ ...deckWithDifferentiationGuidance.slides[0], differentiation_guidance: undefined }],
      render_surface: "teacher",
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).not.toContain("Differentiation guidance");
  });

  it("fails closed if a presentation-surface projection somehow carried differentiation guidance text", async () => {
    const unsafeDeck: SlideDeckData = {
      ...deckWithDifferentiationGuidance,
      slides: [
        {
          ...deckWithDifferentiationGuidance.slides[0],
          blocks: [
            ...deckWithDifferentiationGuidance.slides[0].blocks,
            { block_id: "leaky-block", block_type: "paragraph", body: STRETCH_LEAK_MARKER },
          ],
        },
      ],
    };

    await expect(
      renderArtifact("slide_deck", { ...unsafeDeck, render_surface: "presentation" }),
    ).rejects.toThrow("Student slide deck HTML leaked teacher-only data");
  });
});
