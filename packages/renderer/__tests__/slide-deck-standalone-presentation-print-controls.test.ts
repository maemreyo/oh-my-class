import { describe, expect, it } from "vitest";

import { renderArtifact } from "../src/renderer.js";
import { computeSlideDeckPrintModeClass } from "../src/slide-deck-projection.js";
import type { SlideDeckData } from "../src/contracts/index.js";

// SDH-03: standalone presentation player -- previous/next + keyboard nav +
// progress (already covered by slide-deck-renderer.test.ts), plus this
// slice's new surface: print-mode controls (paged 1/2/4/6 + continuous),
// a chrome/"preview as student" toggle pair gated to teacher/review only,
// and the hash/query/localStorage plumbing that drives them.
//
// The controls are plain <button>s styled as WAI-ARIA radiogroup/switch
// widgets (role="radio"/"switch" + aria-checked), not native <select>/
// <input> -- the sanitizer's BASE_CONFIG (shared by every artifact type,
// including slide_deck) never allowlists those tags, matching every other
// interactive control already in this template (prev/next/print buttons).

const deck: SlideDeckData = {
  deck_id: "deck-print-controls-test",
  title: "Print Controls Mini Deck",
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
      title: "Intro",
      layout: "title",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      blocks: [{ block_id: "block-1", block_type: "heading", body: "Intro" }],
      teacher_notes: {
        facilitation_notes: ["SECRET_FACILITATION_NOTE"],
        answer_key_notes: [],
      },
    },
  ],
  accessibility: { reading_level: "Grade 5", language: "en", alt_text_required: true, keyboard_navigation: true },
  media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: false },
};

describe("computeSlideDeckPrintModeClass (pure, shared by SSR default + client script)", () => {
  it("maps paged layouts to their slides-per-page class", () => {
    expect(computeSlideDeckPrintModeClass("paged", 1)).toBe("print-mode--paged-1");
    expect(computeSlideDeckPrintModeClass("paged", 2)).toBe("print-mode--paged-2");
    expect(computeSlideDeckPrintModeClass("paged", 4)).toBe("print-mode--paged-4");
    expect(computeSlideDeckPrintModeClass("paged", 6)).toBe("print-mode--paged-6");
  });

  it("continuous always wins over slides_per_page", () => {
    expect(computeSlideDeckPrintModeClass("continuous", 1)).toBe("print-mode--continuous");
    expect(computeSlideDeckPrintModeClass("continuous", 6)).toBe("print-mode--continuous");
  });
});

describe("slide_deck standalone print-mode controls (SDH-03)", () => {
  it("defaults the print-mode radiogroup and deck root class to the resolved display preferences", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).toContain('data-deck-id="deck-print-controls-test"');
    expect(html).toContain("slide-deck--presentation slide-deck--student print-mode--paged-1");
    expect(html).toContain('role="radiogroup"');
    expect(html).toContain('data-print-mode-value="print-mode--paged-1"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toMatch(/data-print-mode-value="print-mode--paged-1"[^>]*aria-checked="true"|aria-checked="true"[^>]*data-print-mode-value="print-mode--paged-1"/);
    expect(html).toContain('data-print-mode-value="print-mode--paged-2"');
    expect(html).toContain('data-print-mode-value="print-mode--paged-6"');
    expect(html).toContain('data-print-mode-value="print-mode--continuous"');
    expect(html).toContain("data-slide-print-mode");
  });

  it.each([
    ["paged" as const, 4 as const, "print-mode--paged-4"],
    ["paged" as const, 6 as const, "print-mode--paged-6"],
    ["continuous" as const, 1 as const, "print-mode--continuous"],
  ])("reflects display_preferences (%s, %s) as the initial print-mode class %s", async (print_layout, slides_per_page, expectedClass) => {
    const html = await renderArtifact("slide_deck", {
      ...deck,
      display_preferences: { print_layout, slides_per_page },
    });

    expect(html).toContain("slide-deck--presentation slide-deck--student " + expectedClass);
    expect(html).toContain('data-print-mode-value="' + expectedClass + '" class="slide-print-mode-option slide-print-mode-option--active"');
  });

  it("marks the print-mode CSS class rules for every paged size and the continuous mode", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).toContain(".print-mode--paged-1 .slide-card { page-break-after: always;");
    expect(html).toContain(".print-mode--paged-2 .slide-viewport { grid-template-columns: repeat(2, 1fr); }");
    expect(html).toContain(".print-mode--paged-4 .slide-viewport { grid-template-columns: repeat(2, 1fr); }");
    expect(html).toContain(".print-mode--paged-6 .slide-viewport { grid-template-columns: repeat(3, 1fr); }");
    expect(html).toContain(".print-mode--continuous .slide-card { page-break-after: auto; }");
  });

  it("keeps the presentation-safe navigation/progress markers from the existing player working", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).toContain("data-slide-prev");
    expect(html).toContain("data-slide-next");
    expect(html).toContain("data-slide-progress");
    expect(html).toContain('.slide-deck--js-ready .slide-frame[aria-hidden="true"] { display: none; }');
    expect(html).toContain('.slide-deck--js-ready .slide-frame[aria-hidden="true"] { display: block; }');
  });
});

describe("slide_deck teacher-only toolbar controls never appear on student-clean surfaces (SDH-03)", () => {
  it.each(["student", "presentation"] as const)(
    "omits the chrome and student-preview toggles entirely from %s HTML",
    async (surface) => {
      const html = await renderArtifact("slide_deck", { ...deck, render_surface: surface });

      // The shared client script always *queries* for these selectors (a
      // harmless no-op lookup on a student-safe render), so assert the
      // actual <button> markup is absent, not the bare selector string.
      expect(html).not.toMatch(/<button[^>]*data-slide-chrome-toggle/);
      expect(html).not.toMatch(/<button[^>]*data-slide-teacher-preview/);
      expect(html).not.toContain("Footer in print");
      expect(html).not.toContain("Preview as student");
      // The shared CSS rule referencing "[data-teacher-only]" is harmless
      // (matches nothing on a student-safe render); assert no element in the
      // actual markup carries the attribute.
      expect(html).not.toMatch(/<[a-z][a-z0-9-]*\s[^>]*data-teacher-only/i);
      expect(html).not.toContain("SECRET_FACILITATION_NOTE");
    },
  );

  it.each(["teacher", "review"] as const)(
    "renders the chrome and student-preview toggles on the %s surface, marking teacher-only content data-teacher-only",
    async (surface) => {
      const html = await renderArtifact("slide_deck", { ...deck, render_surface: surface });

      expect(html).toContain("data-slide-chrome-toggle");
      expect(html).toContain("data-slide-teacher-preview");
      expect(html).toContain("Footer in print");
      expect(html).toContain("Preview as student");
      expect(html).toContain('<aside class="teacher-panel" data-teacher-only>');
      expect(html).toContain("SECRET_FACILITATION_NOTE");
    },
  );

  it("seeds the chrome toggle button unchecked when the resolved chrome preference is hidden", async () => {
    const html = await renderArtifact("slide_deck", {
      ...deck,
      render_surface: "teacher",
      display_preferences: { chrome: "hidden" },
    });

    expect(html).toContain('role="switch" aria-checked="false" data-slide-chrome-toggle');
  });

  it("seeds the chrome toggle button checked when the resolved chrome preference allows it", async () => {
    const html = await renderArtifact("slide_deck", {
      ...deck,
      render_surface: "teacher",
      display_preferences: { chrome: "branded" },
    });

    expect(html).toContain('role="switch" aria-checked="true" data-slide-chrome-toggle');
  });

  it("seeds the student-preview toggle unchecked regardless of chrome preference", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "review" });

    expect(html).toContain('role="switch" aria-checked="false" data-slide-teacher-preview');
  });
});

describe("slide_deck standalone controls stay out of printed output (SDH-03)", () => {
  it("keeps the print-mode radiogroup and teacher toggles inside the no-print toolbar header", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "teacher" });
    const toolbarMatch = html.match(/<header class="slide-toolbar no-print">([\s\S]*?)<\/header>/);

    expect(toolbarMatch).not.toBeNull();
    const toolbarHtml = toolbarMatch?.[1] ?? "";
    expect(toolbarHtml).toContain("data-slide-print-mode");
    expect(toolbarHtml).toContain("data-slide-chrome-toggle");
    expect(toolbarHtml).toContain("data-slide-teacher-preview");
  });

  it("keeps the previous/next buttons inside the no-print nav", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "teacher" });
    const navMatch = html.match(/<nav class="slide-controls no-print"[^>]*>([\s\S]*?)<\/nav>/);

    expect(navMatch).not.toBeNull();
    const navHtml = navMatch?.[1] ?? "";
    expect(navHtml).toContain("data-slide-prev");
    expect(navHtml).toContain("data-slide-next");
  });
});

describe("slide_deck standalone hash/query/localStorage plumbing (SDH-03)", () => {
  it("embeds the namespaced localStorage key format and the teacher-only persistence guard", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "teacher" });

    expect(html).toContain("'omc:slide-deck:' + deckId + ':prefs'");
    expect(html).toContain("if (!isTeacherDeck) return;");
    expect(html).toContain("readStoredPrefs");
    expect(html).toContain("writeStoredPrefs");
  });

  it("guards every localStorage access with try/catch so file:// or disabled storage degrades gracefully", async () => {
    const html = await renderArtifact("slide_deck", deck);
    const scriptMatch = html.match(/<script[^>]*>([\s\S]*?)<\/script>/);

    expect(scriptMatch).not.toBeNull();
    const script = scriptMatch?.[1] ?? "";
    expect(script).toContain("window.localStorage.getItem");
    expect(script).toContain("window.localStorage.setItem");
    // Both localStorage call sites live inside their own try block.
    expect(script.match(/try \{/g)?.length ?? 0).toBeGreaterThanOrEqual(3);
  });

  it("reads hash/query overrides for print mode and surface preview without throwing on malformed input", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).toContain("window.location.search");
    expect(html).toContain("window.location.hash");
    expect(html).toContain("query.get('print')");
    expect(html).toContain("query.get('slidesPerPage')");
    expect(html).toContain("query.get('surface')");
  });

  it("guards global arrow/space/home/end key handling against toolbar buttons stealing focus", async () => {
    const html = await renderArtifact("slide_deck", deck);

    expect(html).toContain("event.target.closest('.slide-toolbar')");
  });
});

describe("slide_deck print render_surface stays JS-free (unaffected by SDH-03)", () => {
  it("still renders the dedicated print surface with no embedded script", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "print" });

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("data-slide-print-mode");
  });
});

// SDH-05: production print behavior -- full deck (not just the active
// slide), paged 1/2/4/6-up grid + continuous mode, real 16:9 aspect-ratio
// sizing (no transform scale), a single crisp border owner per card with no
// print shadow/filter/transform, and controls hidden in print. Extracts the
// `<style>` and `@media print { ... }` block content so assertions are about
// the actual CSS the browser would apply, not just substring presence.
function extractStyleBlock(html: string): string {
  const match = html.match(/<style>([\s\S]*?)<\/style>/);
  if (!match) throw new Error("no <style> block found");
  return match[1];
}

// base.html's own tiny `@media print { .no-print {...} }` rule is baked into
// every render's <style> block ahead of slide_deck's pageCSS -- take the
// *last* `@media print` occurrence, which is the slide_deck-specific one.
function extractPrintMediaBlock(css: string): string {
  const startIndex = css.lastIndexOf("@media print");
  if (startIndex === -1) throw new Error("no @media print block found");
  const openBraceIndex = css.indexOf("{", startIndex);
  let depth = 1;
  let index = openBraceIndex + 1;
  while (depth > 0 && index < css.length) {
    if (css[index] === "{") depth++;
    if (css[index] === "}") depth--;
    index++;
  }
  return css.slice(openBraceIndex + 1, index - 1);
}

// Grabs the declaration body of the first standalone `.slide-card { ... }`
// rule (not `.slide-card--<layout>` and not a compound selector list) inside
// the print block -- this is the one rule that owns the card's border in
// print, per SDH-05's "single border owner" requirement.
function extractSlideCardRuleBody(printBlock: string): string {
  const match = printBlock.match(/(?:^|\s)\.slide-card\s*\{([^}]*)\}/);
  if (!match) throw new Error("no standalone .slide-card rule found in print block");
  return match[1];
}

describe("slide_deck print layout and border fidelity (SDH-05)", () => {
  it("carries the resolved print-mode class on both the interactive player and the dedicated print surface roots", async () => {
    const presentationHtml = await renderArtifact("slide_deck", {
      ...deck,
      display_preferences: { print_layout: "paged", slides_per_page: 4 },
    });
    const printHtml = await renderArtifact("slide_deck", {
      ...deck,
      render_surface: "print",
      display_preferences: { print_layout: "paged", slides_per_page: 4 },
    });

    expect(presentationHtml).toMatch(/class="slide-deck[^"]*print-mode--paged-4[^"]*"/);
    expect(printHtml).toMatch(/class="slide-deck[^"]*print-mode--paged-4[^"]*"/);
  });

  it("gives the dedicated print surface the continuous class too", async () => {
    const printHtml = await renderArtifact("slide_deck", {
      ...deck,
      render_surface: "print",
      display_preferences: { print_layout: "continuous" },
    });

    expect(printHtml).toMatch(/class="slide-deck[^"]*print-mode--continuous[^"]*"/);
  });

  it("renders every slide in the dedicated print surface's DOM with no active-slide gating at all", async () => {
    const twoSlideDeck = { ...deck, slides: [...deck.slides, { ...deck.slides[0], slide_id: "slide-2", title: "Second" }] };
    const html = await renderArtifact("slide_deck", { ...twoSlideDeck, render_surface: "print" });
    const mainMatch = html.match(/<main id="main-content">([\s\S]*?)<\/main>/);
    const mainHtml = mainMatch?.[1] ?? "";

    // The CSS block legitimately contains the *string* "aria-hidden" as part
    // of an attribute-selector (`[aria-hidden="true"]`) -- only the actual
    // rendered markup (inside <main>) must never gate a slide on it.
    expect(mainHtml).not.toContain("aria-hidden");
    expect((mainHtml.match(/class="slide-card/g) ?? []).length).toBe(2);
  });

  it("renders every slide frame in the interactive player's DOM even though only slide 0 starts visible", async () => {
    const twoSlideDeck = { ...deck, slides: [...deck.slides, { ...deck.slides[0], slide_id: "slide-2", title: "Second" }] };
    const html = await renderArtifact("slide_deck", twoSlideDeck);

    expect((html.match(/data-slide data-slide-index="/g) ?? []).length).toBe(2);
    expect(html).toContain('aria-hidden="false"');
    expect(html).toContain('aria-hidden="true"');
  });

  it("defeats the screen-only single-active-slide rule inside @media print", async () => {
    const printBlock = extractPrintMediaBlock(extractStyleBlock(await renderArtifact("slide_deck", deck)));

    expect(printBlock).toContain('.slide-deck--js-ready .slide-frame[aria-hidden="true"] { display: block; }');
    expect(printBlock).toContain(".slide-frame { display: block; }");
  });

  it("hides print controls/navigation inside @media print", async () => {
    const printBlock = extractPrintMediaBlock(extractStyleBlock(await renderArtifact("slide_deck", deck)));

    expect(printBlock).toMatch(/\.slide-toolbar[^{]*\{[^}]*display:\s*none/);
    expect(printBlock).toMatch(/\.slide-controls[^{]*\{[^}]*display:\s*none/);
  });

  it("sizes the printed slide card with a real 16:9 aspect-ratio, never a transform scale", async () => {
    const printBlock = extractPrintMediaBlock(extractStyleBlock(await renderArtifact("slide_deck", deck)));
    const cardRule = extractSlideCardRuleBody(printBlock);

    expect(cardRule).toMatch(/aspect-ratio:\s*16\s*\/\s*9/);
    expect(cardRule).not.toMatch(/transform:\s+(?!none\b)/);
  });

  it("supports paged grids for 1/2/4/6 slides per page and lets continuous mode ignore the grid", async () => {
    const printBlock = extractPrintMediaBlock(extractStyleBlock(await renderArtifact("slide_deck", deck)));

    expect(printBlock).toContain(".print-mode--paged-1 .slide-card { page-break-after: always; page-break-inside: avoid; }");
    expect(printBlock).toContain(".print-mode--paged-2 .slide-viewport { grid-template-columns: repeat(2, 1fr); }");
    expect(printBlock).toContain(".print-mode--paged-2 .slide-list { grid-template-columns: repeat(2, 1fr); }");
    expect(printBlock).toContain(".print-mode--paged-4 .slide-viewport { grid-template-columns: repeat(2, 1fr); }");
    expect(printBlock).toContain(".print-mode--paged-4 .slide-list { grid-template-columns: repeat(2, 1fr); }");
    expect(printBlock).toContain(".print-mode--paged-6 .slide-viewport { grid-template-columns: repeat(3, 1fr); }");
    expect(printBlock).toContain(".print-mode--paged-6 .slide-list { grid-template-columns: repeat(3, 1fr); }");
    expect(printBlock).toContain(".print-mode--continuous .slide-card { page-break-after: auto; }");
    expect(printBlock).toContain(".print-mode--continuous .slide-viewport, .print-mode--continuous .slide-list { grid-template-columns: 1fr; }");
  });

  it("owns the card border with exactly one rule in print and zeroes out shadow/filter/transform", async () => {
    const printBlock = extractPrintMediaBlock(extractStyleBlock(await renderArtifact("slide_deck", deck)));
    const cardRule = extractSlideCardRuleBody(printBlock);

    // Exactly one element (the card itself) declares a `border` anywhere in
    // the print block -- no wrapper/frame/viewport rule adds a second one.
    expect(printBlock.match(/\bborder:\s*\d/g)?.length).toBe(1);
    expect(cardRule.match(/\bborder:/g)?.length).toBe(1);
    expect(cardRule).toMatch(/box-shadow:\s*none/);
    expect(cardRule).toMatch(/filter:\s*none/);
    expect(cardRule).toMatch(/transform:\s*none/);
    // No shadow/filter/transform value other than the explicit "none" reset.
    expect(cardRule).not.toMatch(/box-shadow:\s+(?!none\b)/);
    expect(cardRule).not.toMatch(/filter:\s+(?!none\b)/);
    expect(cardRule).not.toMatch(/transform:\s+(?!none\b)/);
  });

  it("keeps the print rules fully inside @media print -- mobile screen styles stay untouched", async () => {
    const css = extractStyleBlock(await renderArtifact("slide_deck", deck));
    const mobileBlockMatch = css.match(/@media \(max-width: 640px\) \{([\s\S]*?)\n {4}\}/);

    expect(mobileBlockMatch).not.toBeNull();
    const mobileBlock = mobileBlockMatch?.[1] ?? "";
    expect(mobileBlock).not.toContain("aspect-ratio");
    expect(mobileBlock).not.toContain("print-mode--paged");
    expect(mobileBlock).toContain(".slide-nav-button, .slide-print, .slide-print-mode, .slide-toggle-button { width: 100%;");
  });
});
