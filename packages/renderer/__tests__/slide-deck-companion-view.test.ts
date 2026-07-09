import { describe, expect, it } from "vitest";

import { projectSlideDeckCompanionCards } from "../src/slide-deck-projection.js";
import type { SlideDeckData } from "../src/contracts/index.js";

// ADR-045 (SDTF-04): architecture/contract-only slice for a future
// mobile-readable "companion view" -- a student's own-device view of
// interaction prompts, distinct from the projector/presentation mirroring
// covered by slide-deck-surface-and-chrome-policy.test.ts. No live UI, sync,
// join/auth, or response persistence exists yet; this suite only proves the
// projection *shape* is correct and structurally student-safe today.

const LEAK_RATIONALE = "LEAK_RATIONALE only a teacher should ever see this";
const LEAK_ACCEPTABLE_ANSWER = "LEAK_ACCEPTABLE_ANSWER";

const deck: SlideDeckData = {
  deck_id: "deck-companion-test",
  title: "Companion View Deck",
  locale: "en-US",
  theme: "default",
  surfaces: {
    student: { mode: "presentation", export_format: "html" },
    teacher: { mode: "teacher_guide", export_format: "html" },
    print: { mode: "print", export_format: "html" },
  },
  slides: [
    {
      slide_id: "slide-1",
      title: "Quick Check",
      layout: "question",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      blocks: [{ block_id: "block-1", block_type: "heading", body: "Quick Check" }],
      teacher_notes: {
        facilitation_notes: ["LEAK_FACILITATION_NOTE"],
        answer_key_notes: ["LEAK_ANSWER_KEY_NOTE"],
      },
      interactions: [
        {
          interaction_id: "interaction-1",
          interaction_type: "multiple_choice_single",
          prompt: "Which fraction is equivalent to 1/2?",
          answer_bearing: true,
          options: [
            { option_id: "a", label: "2/4" },
            { option_id: "b", label: "1/3" },
          ],
          teacher_only: {
            separation: "teacher_only_projection",
            correct_option_ids: ["a"],
            acceptable_answers: [LEAK_ACCEPTABLE_ANSWER],
            rationale: LEAK_RATIONALE,
          },
          no_js_fallback: "Discuss aloud without recording responses.",
          accessibility_label: "Multiple choice: equivalent fractions",
        },
      ],
    },
    {
      slide_id: "slide-2",
      title: "Exit Ticket",
      layout: "summary",
      progression: { step_index: 2, reveal_policy: "all_at_once" },
      blocks: [{ block_id: "block-2", block_type: "paragraph", body: "Wrap up." }],
      interactions: [
        {
          interaction_id: "interaction-2",
          interaction_type: "exit_ticket",
          prompt: "Write one thing you learned today.",
        },
      ],
    },
  ],
  accessibility: { reading_level: "Grade 5", language: "en", alt_text_required: true, keyboard_navigation: true },
  media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: false },
};

describe("slide deck companion view projection", () => {
  it("derives one card per interaction, keyed by stable slide/interaction IDs", () => {
    const companion = projectSlideDeckCompanionCards(deck);

    expect(companion.title).toBe("Companion View Deck");
    expect(companion.lang).toBe("en");
    expect(companion.cards).toEqual([
      {
        slideId: "slide-1",
        interactionId: "interaction-1",
        prompt: "Which fraction is equivalent to 1/2?",
        responseIntent: "multiple_choice_single",
        noJsFallback: "Discuss aloud without recording responses.",
        accessibilityLabel: "Multiple choice: equivalent fractions",
      },
      {
        slideId: "slide-2",
        interactionId: "interaction-2",
        prompt: "Write one thing you learned today.",
        responseIntent: "exit_ticket",
        noJsFallback: "Use this prompt without storing student responses.",
        accessibilityLabel: "Slide interaction",
      },
    ]);
  });

  it("round-trips interaction IDs so future companion cards can bind back to their slide prompt", () => {
    const companion = projectSlideDeckCompanionCards(deck);
    const originalIds = deck.slides.flatMap((slide) => (slide.interactions ?? []).map((i) => i.interaction_id));

    expect(companion.cards.map((card) => card.interactionId)).toEqual(originalIds);
  });

  it("never carries teacher-only rationale or answer-key content, even structurally", () => {
    const companion = projectSlideDeckCompanionCards(deck);
    const serialized = JSON.stringify(companion);

    expect(serialized).not.toContain(LEAK_RATIONALE);
    expect(serialized).not.toContain(LEAK_ACCEPTABLE_ANSWER);
    expect(serialized).not.toContain("LEAK_FACILITATION_NOTE");
    expect(serialized).not.toContain("LEAK_ANSWER_KEY_NOTE");

    // Structural guarantee, not just a string scan: the card shape has no
    // field that could ever hold teacher-only guidance/answers/notes.
    const cardKeys = Object.keys(companion.cards[0]);
    expect(cardKeys).toEqual(["slideId", "interactionId", "prompt", "responseIntent", "noJsFallback", "accessibilityLabel"]);
  });

  it("clamps to a student-safe surface even if asked for teacher/review, so teacher data can never reach a companion card", () => {
    const teacherRequested = projectSlideDeckCompanionCards({ ...deck, render_surface: "teacher" });
    const reviewRequested = projectSlideDeckCompanionCards(deck, "review");

    for (const companion of [teacherRequested, reviewRequested]) {
      expect(companion.surface).not.toBe("teacher");
      expect(companion.surface).not.toBe("review");
      const serialized = JSON.stringify(companion);
      expect(serialized).not.toContain(LEAK_RATIONALE);
      expect(serialized).not.toContain(LEAK_ACCEPTABLE_ANSWER);
    }
  });

  it("carries no slide layout, block, or pixel/aspect-ratio field -- nothing forces mobile content into projector (16:9) scaling", () => {
    const companion = projectSlideDeckCompanionCards(deck);

    const forbiddenKeys = ["layout", "blocks", "width", "height", "aspectRatio", "revealPolicy"];
    const presentKeys = new Set([...Object.keys(companion), ...companion.cards.flatMap((card) => Object.keys(card))]);
    for (const forbidden of forbiddenKeys) {
      expect(presentKeys.has(forbidden)).toBe(false);
    }
  });
});
