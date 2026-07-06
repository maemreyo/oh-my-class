import { describe, expect, it } from "vitest";

import { renderAgentArtifact } from "../src/agent-renderer.js";
import { renderArtifact } from "../src/renderer.js";
import type { SlideDeckData } from "../src/contracts/index.js";

const deck: SlideDeckData = {
  deck_id: "deck-render-test",
  title: "Equivalent Fractions Mini Deck",
  locale: "en-US",
  theme: "default",
  surfaces: {
    student: { mode: "presentation", export_format: "html" },
    teacher: { mode: "teacher_guide", export_format: "html" },
    print: { mode: "print", export_format: "html" },
  },
  source_refs: [
    {
      source_id: "src-fractions-standard",
      title: "Grade 5 Fractions Standard",
      citation: "CCSS 5.NF.A",
      confidence: "verified",
    },
  ],
  slides: [
    {
      slide_id: "slide-title",
      title: "Equivalent Fractions",
      layout: "title",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      blocks: [
        {
          block_id: "block-title",
          block_type: "heading",
          body: "Equivalent Fractions",
          source_ref_ids: ["src-fractions-standard"],
        },
      ],
      teacher_notes: {
        facilitation_notes: ["SECRET_TEACHER_NOTE"],
        answer_key_notes: [],
      },
    },
    {
      slide_id: "slide-check",
      title: "Quick Check",
      layout: "question",
      progression: { step_index: 2, reveal_policy: "progressive" },
      blocks: [
        {
          block_id: "block-question",
          block_type: "interaction_prompt",
          body: "Which fraction equals 1/2?",
        },
      ],
      interactions: [
        {
          interaction_id: "interaction-check",
          interaction_type: "multiple_choice_single",
          prompt: "Which fraction equals 1/2?",
          answer_bearing: true,
          options: [
            { option_id: "a", label: "1/3" },
            { option_id: "b", label: "2/4" },
          ],
          teacher_only: {
            separation: "teacher_only_projection",
            correct_option_ids: ["b"],
            rationale: "SECRET_RATIONALE",
          },
        },
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

describe("slide_deck renderer", () => {
  it("renders standalone slide deck HTML without external assets", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain('name="viewport"');
    expect(html).toContain("oh-my-class");
    expect(html).toContain("Equivalent Fractions Mini Deck");
    expect(html).not.toMatch(/https?:\/\//i);
    expect(html).not.toMatch(/<link\s/i);
    expect(html).not.toMatch(/@import/i);
  });

  it("does not expose teacher-only answers or notes in student HTML", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).not.toContain("SECRET_TEACHER_NOTE");
    expect(html).not.toContain("SECRET_RATIONALE");
    expect(html).not.toContain("correct_option_ids");
  });

  it("renders teacher guide surface with facilitation notes and answer guidance", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "teacher" });

    expect(html).toContain("Teacher guide");
    expect(html).toContain("SECRET_TEACHER_NOTE");
    expect(html).toContain("SECRET_RATIONALE");
    expect(html).toContain("Correct");
  });

  it("renders print surface with page breaks and expanded reveals", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "print" });

    expect(html).toContain("Print handout");
    expect(html).toContain("page-break-after: always");
    expect(html).toContain("all at once");
    expect(html).not.toContain("SECRET_TEACHER_NOTE");
  });

  it("fails closed when student HTML contains projected teacher-only data", async () => {
    const unsafeDeck: SlideDeckData = {
      ...deck,
      slides: [
        {
          ...deck.slides[0],
          blocks: [
            ...deck.slides[0].blocks,
            { block_id: "leaky-block", block_type: "paragraph", body: "SECRET_TEACHER_NOTE" },
          ],
        },
      ],
    };

    await expect(renderArtifact("slide_deck", unsafeDeck)).rejects.toThrow("Student slide deck HTML leaked teacher-only data");
  });

  it("renders slide_deck ArtifactContent through the agent renderer", async () => {
    const html = await renderAgentArtifact({
      artifact_type: "slide_deck",
      theme: "default",
      title: deck.title,
      sections: [{ title: "Deck", slide_deck: deck }],
      metadata: { slide_deck_data: deck },
      accessibility: { language: "en" },
    });

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("Equivalent Fractions Mini Deck");
    expect(html).not.toMatch(/https?:\/\//i);
  });

  it("renders registered interaction fallbacks and online media warnings", async () => {
    const html = await renderArtifact("slide_deck", {
      ...deck,
      slides: [
        {
          ...deck.slides[0],
          blocks: [
            {
              block_id: "online-block",
              block_type: "image",
              body: "Optional video model",
              media: {
                media_id: "online-video",
                media_type: "video",
                source: "https://example.com/video",
                tier: "online_optional",
                alt_text: "Video model for fractions",
                fallback_text: "Use the printed fraction-bar model.",
                requires_network: true,
              },
            },
          ],
          interactions: [
            {
              interaction_id: "poll-1",
              interaction_type: "poll_prompt",
              prompt: "Which model helped most?",
              no_js_fallback: "Run as a show-of-hands poll.",
              accessibility_label: "Poll prompt",
            },
          ],
        },
      ],
    });

    expect(html).toContain("Optional online media requires network access");
    expect(html).toContain("Use the printed fraction-bar model.");
    expect(html).toContain("No-JS fallback: Run as a show-of-hands poll.");
    expect(html).not.toContain("correct_option_ids");
  });
});
