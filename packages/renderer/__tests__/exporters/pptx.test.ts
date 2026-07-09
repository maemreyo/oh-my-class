import { describe, expect, it } from "vitest";
import { unzipSync } from "fflate";

import { PPTXExporter, SlideDeckUnsupportedLayoutError } from "../../src/exporters/pptx/index.js";
import type { SlideDeckData } from "../../src/contracts/index.js";

const ONE_BY_ONE_PNG_DATA_URI =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

const deck: SlideDeckData = {
  deck_id: "deck-pptx-test",
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
      slide_id: "slide-title",
      title: "Equivalent Fractions",
      layout: "title",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      blocks: [
        { block_id: "block-title", block_type: "heading", body: "Equivalent Fractions" },
        {
          block_id: "block-image",
          block_type: "image",
          body: "A fraction bar model",
          media: {
            media_id: "media-fraction-bar",
            media_type: "image",
            source: ONE_BY_ONE_PNG_DATA_URI,
            tier: "packaged",
            alt_text: "Fraction bar model showing 1/2 equals 2/4",
          },
        },
      ],
      teacher_notes: { facilitation_notes: ["SECRET_TEACHER_NOTE"], answer_key_notes: [] },
    },
    {
      slide_id: "slide-check",
      title: "Quick Check",
      layout: "question",
      progression: { step_index: 2, reveal_policy: "progressive" },
      blocks: [{ block_id: "block-question", block_type: "paragraph", body: "Which fraction equals 1/2?" }],
      interactions: [
        {
          interaction_id: "interaction-check",
          interaction_type: "multiple_choice_single",
          prompt: "Which fraction equals 1/2?",
          options: [
            { option_id: "opt-a", label: "2/4" },
            { option_id: "opt-b", label: "1/3" },
          ],
          teacher_only: {
            separation: "teacher_only_projection",
            correct_option_ids: ["opt-a"],
            rationale: "SECRET_RATIONALE",
          },
        },
      ],
    },
  ],
  accessibility: { reading_level: "grade-5", language: "en", alt_text_required: true, keyboard_navigation: true },
  media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: true },
};

function slideEntryCount(pptxBytes: Buffer): number {
  const files = unzipSync(new Uint8Array(pptxBytes));
  return Object.keys(files).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name)).length;
}

describe("PPTXExporter", () => {
  it("exports a SlideDeckData deck to a valid OOXML .pptx with one slide per deck slide", async () => {
    const bytes = await new PPTXExporter().export(deck, "student");

    const files = unzipSync(new Uint8Array(bytes));
    expect(Object.keys(files)).toContain("[Content_Types].xml");
    expect(Object.keys(files)).toContain("ppt/presentation.xml");
    expect(slideEntryCount(bytes)).toBe(deck.slides.length);
  });

  it("never leaks teacher-only data into the student export", async () => {
    const bytes = await new PPTXExporter().export(deck, "student");

    const files = unzipSync(new Uint8Array(bytes));
    const xml = Object.entries(files)
      .filter(([name]) => name.startsWith("ppt/slides/"))
      .map(([, data]) => Buffer.from(data).toString("utf-8"))
      .join("\n");

    expect(xml).not.toContain("SECRET_TEACHER_NOTE");
    expect(xml).not.toContain("SECRET_RATIONALE");
  });

  it("includes teacher-only facilitation notes as speaker notes on the teacher export", async () => {
    const bytes = await new PPTXExporter().export(deck, "teacher");

    const files = unzipSync(new Uint8Array(bytes));
    const notesXml = Object.entries(files)
      .filter(([name]) => name.startsWith("ppt/notesSlides/"))
      .map(([, data]) => Buffer.from(data).toString("utf-8"))
      .join("\n");

    expect(notesXml).toContain("SECRET_TEACHER_NOTE");
  });

  it("fails closed for a layout with no renderer template yet, instead of a blank/wrong slide", async () => {
    const unsupportedDeck: SlideDeckData = {
      ...deck,
      slides: [{ ...deck.slides[0], layout: "cover" }],
    };

    await expect(new PPTXExporter().export(unsupportedDeck)).rejects.toBeInstanceOf(
      SlideDeckUnsupportedLayoutError,
    );
  });
});
