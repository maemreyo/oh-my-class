import { describe, expect, it } from "vitest";

import {
  SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS,
  resolveSlideDeckDisplayPreferences,
} from "../src/contracts/slide_deck.js";
import { projectSlideDeckSurface } from "../src/slide-deck-projection.js";
import type { SlideDeckData } from "../src/contracts/index.js";

const legacyDeck: SlideDeckData = {
  deck_id: "deck-legacy",
  title: "Legacy Deck",
  locale: "en-US",
  surfaces: {
    student: { mode: "presentation", export_format: "html" },
    teacher: { mode: "teacher_guide", export_format: "html" },
    print: { mode: "print", export_format: "html" },
  },
  slides: [
    {
      slide_id: "slide-1",
      title: "Intro",
      layout: "title",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      blocks: [{ block_id: "block-1", block_type: "heading", body: "Intro" }],
    },
  ],
  accessibility: { reading_level: "Grade 5", language: "en", alt_text_required: true, keyboard_navigation: true },
  media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: false },
};

describe("resolveSlideDeckDisplayPreferences", () => {
  it("defaults match ADR-043 production-safe values when nothing is supplied", () => {
    expect(resolveSlideDeckDisplayPreferences(undefined)).toEqual(SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS);
    expect(resolveSlideDeckDisplayPreferences(null)).toEqual(SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS);
    expect(resolveSlideDeckDisplayPreferences({})).toEqual({
      surface: "presentation",
      print_layout: "paged",
      slides_per_page: 1,
      chrome: "hidden",
    });
  });

  it("falls back field-by-field on invalid options instead of throwing", () => {
    const resolved = resolveSlideDeckDisplayPreferences({
      surface: "print",
      print_layout: "sideways",
      slides_per_page: 3,
      chrome: "very_loud",
    });

    expect(resolved).toEqual({
      surface: "print",
      print_layout: "paged",
      slides_per_page: 1,
      chrome: "hidden",
    });
  });

  it("only accepts the valid slides-per-page values", () => {
    for (const valid of [1, 2, 4, 6] as const) {
      expect(resolveSlideDeckDisplayPreferences({ slides_per_page: valid }).slides_per_page).toBe(valid);
    }
    expect(resolveSlideDeckDisplayPreferences({ slides_per_page: 5 }).slides_per_page).toBe(1);
    expect(resolveSlideDeckDisplayPreferences({ slides_per_page: "2" }).slides_per_page).toBe(1);
  });
});

describe("slide deck projection backward compatibility", () => {
  it("projects a deck with no display_preferences field using safe defaults", () => {
    const projected = projectSlideDeckSurface(legacyDeck);

    expect(projected.displayPreferences).toEqual(SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS);
  });

  it("resolves a partially-populated legacy display_preferences value", () => {
    const projected = projectSlideDeckSurface({
      ...legacyDeck,
      display_preferences: { print_layout: "continuous" },
    });

    expect(projected.displayPreferences).toEqual({
      surface: "presentation",
      print_layout: "continuous",
      slides_per_page: 1,
      chrome: "hidden",
    });
  });
});
