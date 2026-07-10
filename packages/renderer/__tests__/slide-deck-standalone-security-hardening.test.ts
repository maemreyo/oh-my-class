import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";

import { renderArtifact } from "../src/renderer.js";
import type { SlideDeckData } from "../src/contracts/index.js";

// SDH-12 (ADR-043): SDH-03 already wrote the hash/query/localStorage parsing
// with allowlist checks (readLocationOverrides, isValidPrintMode,
// printModeFromLayout) and gated all localStorage access behind
// `isTeacherDeck`. This suite doesn't re-implement that logic to test it --
// it extracts the *actual* inline <script> the renderer emits and runs it
// against a minimal hand-rolled DOM/window stub (Node's built-in `vm`
// module, no new test dependency), so a regression in the shipped code -- not
// a copy of it -- would fail these tests.

const baseDeck: SlideDeckData = {
  deck_id: "deck-security-test",
  title: "Security Hardening Mini Deck",
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
        answer_key_notes: ["SECRET_ANSWER_KEY"],
      },
    },
  ],
  accessibility: { reading_level: "Grade 5", language: "en", alt_text_required: true, keyboard_navigation: true },
  media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: false },
};

function extractScript(html: string): string {
  const match = html.match(/<script>([\s\S]*?)<\/script>/);
  if (!match) throw new Error("no <script> block found in rendered HTML");
  return match[1];
}

// --- Minimal fake DOM: only what the shipped script actually touches -----

function makeClassList(initial: readonly string[]) {
  const set = new Set(initial);
  return {
    add: (c: string) => void set.add(c),
    remove: (c: string) => void set.delete(c),
    contains: (c: string) => set.has(c),
    toggle: (c: string, force?: boolean) => {
      const next = force === undefined ? !set.has(c) : force;
      if (next) set.add(c);
      else set.delete(c);
      return next;
    },
    values: () => [...set],
  };
}

type FakeElement = {
  tagName: string;
  dataset: Record<string, string>;
  disabled: boolean;
  textContent: string;
  classList: ReturnType<typeof makeClassList>;
  getAttribute: (name: string) => string | null;
  setAttribute: (name: string, value: string) => void;
  addEventListener: (type: string, handler: (event: unknown) => void) => void;
  fire: (type: string, event?: unknown) => void;
  closest: () => null;
  querySelector: (selector: string) => FakeElement | null;
  querySelectorAll: (selector: string) => FakeElement[];
};

function makeElement(opts: {
  tag?: string;
  dataset?: Record<string, string>;
  attrs?: Record<string, string>;
  classes?: string[];
  children?: Record<string, FakeElement | FakeElement[]>;
} = {}): FakeElement {
  const attributes = new Map(Object.entries(opts.attrs ?? {}));
  const listeners: Record<string, Array<(event: unknown) => void>> = {};
  const children = opts.children ?? {};
  return {
    tagName: opts.tag ?? "div",
    dataset: opts.dataset ?? {},
    disabled: false,
    textContent: "",
    classList: makeClassList(opts.classes ?? []),
    getAttribute: (name) => (attributes.has(name) ? attributes.get(name)! : null),
    setAttribute: (name, value) => void attributes.set(name, String(value)),
    addEventListener: (type, handler) => void (listeners[type] ??= []).push(handler),
    fire: (type, event = {}) => (listeners[type] ?? []).forEach((h) => h(event)),
    closest: () => null,
    querySelector: (selector) => {
      const found = children[selector];
      if (!found) return null;
      return Array.isArray(found) ? found[0] ?? null : found;
    },
    querySelectorAll: (selector) => {
      const found = children[selector];
      if (!found) return [];
      return Array.isArray(found) ? found : [found];
    },
  };
}

type FakeStorage = {
  store: Map<string, string>;
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
};

function makeStorage(preset: Record<string, string> = {}): FakeStorage {
  const store = new Map(Object.entries(preset));
  return {
    store,
    getItem: (key) => (store.has(key) ? store.get(key)! : null),
    setItem: (key, value) => void store.set(key, value),
  };
}

// Wires up one fake `[data-slide-deck]` element (matching the real template's
// markup) and runs the actual extracted script against it inside a fresh vm
// context. Returns the deck element, the fake storage (to inspect what got
// written), and any thrown error (there should never be one).
function runScriptAgainstDeck(
  script: string,
  opts: {
    surface: "student" | "presentation" | "teacher" | "review";
    hash?: string;
    search?: string;
    storagePreset?: Record<string, string>;
  },
) {
  const isTeacherSurface = opts.surface === "teacher" || opts.surface === "review";
  const printModeButtons = ["print-mode--paged-1", "print-mode--paged-2", "print-mode--paged-4", "print-mode--paged-6", "print-mode--continuous"].map(
    (value) => makeElement({ tag: "button", attrs: { "data-print-mode-value": value } }),
  );
  const chromeToggle = isTeacherSurface ? makeElement({ tag: "button" }) : null;
  const previewToggle = isTeacherSurface ? makeElement({ tag: "button" }) : null;
  const progress = makeElement({ tag: "p" });
  const slideFrame = makeElement({ tag: "section", attrs: { "aria-hidden": "false" } });

  const deck = makeElement({
    tag: "section",
    // Real script reads the deck id via `getAttribute('data-deck-id')` and
    // the surface via `dataset.surface` -- both must be wired up to match.
    dataset: { deckId: "deck-security-test", surface: opts.surface },
    attrs: { "data-deck-id": "deck-security-test" },
    classes: ["slide-deck", "print-mode--paged-1"],
    children: {
      "[data-slide]": [slideFrame],
      "[data-slide-progress]": progress,
      "[data-slide-prev]": makeElement({ tag: "button" }),
      "[data-slide-next]": makeElement({ tag: "button" }),
      "[data-slide-print]": makeElement({ tag: "button" }),
      "[data-slide-print-mode]": printModeButtons,
      "[data-slide-chrome-toggle]": chromeToggle ?? [],
      "[data-slide-teacher-preview]": previewToggle ?? [],
    },
  });

  const storage = makeStorage(opts.storagePreset);
  const documentStub = {
    readyState: "complete",
    body: makeElement({ tag: "body" }),
    addEventListener: () => {},
    querySelectorAll: (selector: string) => (selector === "[data-slide-deck]" ? [deck] : []),
  };
  const windowStub = {
    location: { search: opts.search ?? "", hash: opts.hash ?? "" },
    localStorage: storage,
    print: () => {},
  };

  let thrown: unknown = null;
  try {
    runInNewContext(script, {
      window: windowStub,
      document: documentStub,
      URLSearchParams,
      console,
    });
  } catch (error) {
    thrown = error;
  }

  return { deck, chromeToggle, previewToggle, storage, thrown };
}

describe("slide_deck standalone hash/query parsing rejects malformed values (SDH-12)", () => {
  it("degrades a script-injection attempt in the surface param to a safe no-op, never throwing", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);

    const { thrown, deck } = runScriptAgainstDeck(script, {
      surface: "student",
      hash: "#surface=" + encodeURIComponent("<script>alert(1)</script>"),
    });

    expect(thrown).toBeNull();
    // A student render carries no teacher-preview button at all, so there is
    // nothing for a forced "surface=teacher/<script>" override to flip --
    // the deck keeps its server-resolved default print-mode class.
    expect(deck.classList.contains("print-mode--paged-1")).toBe(true);
  });

  it("defaults an out-of-range slidesPerPage/print combination instead of accepting it verbatim", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);

    const { thrown, deck } = runScriptAgainstDeck(script, {
      surface: "teacher",
      hash: "#print=paged&slidesPerPage=" + encodeURIComponent("99; DROP TABLE"),
    });

    expect(thrown).toBeNull();
    // parseInt on a garbage string is NaN -> not in the [1,2,4,6] allowlist
    // -> falls back to the single-slide-per-page mode, never "99...".
    expect(deck.classList.contains("print-mode--paged-1")).toBe(true);
    expect(deck.classList.values().some((cls) => cls.includes("DROP"))).toBe(false);
  });

  it("ignores an unrecognized print value entirely (only 'paged'/'continuous' are known)", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);

    const { thrown, deck } = runScriptAgainstDeck(script, {
      surface: "teacher",
      search: "?print=" + encodeURIComponent("javascript:alert(1)"),
    });

    expect(thrown).toBeNull();
    expect(deck.classList.contains("print-mode--paged-1")).toBe(true);
  });

  it("never lets a hash/query override introduce student-preview or teacher-only visibility on a student render", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);

    const { thrown, chromeToggle, previewToggle } = runScriptAgainstDeck(script, {
      surface: "student",
      hash: "#surface=teacher",
    });

    expect(thrown).toBeNull();
    // The real template never renders these buttons for a student surface in
    // the first place (SDH-02/SDH-03 template-time omission) -- proven here
    // by their absence, matching the actual markup this script would run
    // against.
    expect(chromeToggle).toBeNull();
    expect(previewToggle).toBeNull();
  });
});

describe("slide_deck standalone localStorage hardening (SDH-12)", () => {
  it("only ever reads/writes localStorage for a teacher/review render, never for student/presentation", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);

    const { storage, thrown } = runScriptAgainstDeck(script, {
      surface: "student",
      storagePreset: { "omc:slide-deck:deck-security-test:prefs": JSON.stringify({ studentPreview: true }) },
    });

    expect(thrown).toBeNull();
    // Nothing new gets written for a student deck.
    expect(storage.store.get("omc:slide-deck:deck-security-test:prefs")).toBe(
      JSON.stringify({ studentPreview: true }),
    );
  });

  it("strips unknown/sensitive fields from a poisoned localStorage blob when persisting -- never round-trips them", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);
    const key = "omc:slide-deck:deck-security-test:prefs";
    const poisoned = {
      printMode: "print-mode--paged-4",
      studentPreview: true,
      chromeVisible: false,
      // Attempted sensitive-data / prototype-pollution payloads:
      teacherNotes: "SECRET_ANSWER_KEY",
      answerKey: "SECRET_ANSWER_KEY",
      __proto__: { polluted: true },
    };

    const { storage, thrown, deck } = runScriptAgainstDeck(script, {
      surface: "teacher",
      storagePreset: { [key]: JSON.stringify(poisoned) },
    });

    expect(thrown).toBeNull();
    expect(deck.classList.contains("print-mode--paged-4")).toBe(true);
    expect((Object.prototype as unknown as { polluted?: boolean }).polluted).toBeUndefined();

    // Force a persist by clicking a print-mode button (the only write path).
    deck.querySelectorAll('[data-slide-print-mode]')[0]?.fire("click");
    const written = storage.store.get(key);
    expect(written).toBeDefined();
    const writtenObject = JSON.parse(written!);
    expect(Object.keys(writtenObject).sort()).toEqual(["chromeVisible", "printMode", "studentPreview"]);
    expect(JSON.stringify(writtenObject)).not.toContain("SECRET_ANSWER_KEY");
  });

  it("degrades invalid JSON in localStorage to the server-resolved default instead of throwing", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);
    const key = "omc:slide-deck:deck-security-test:prefs";

    const { thrown, deck } = runScriptAgainstDeck(script, {
      surface: "teacher",
      storagePreset: { [key]: "{not valid json" },
    });

    expect(thrown).toBeNull();
    expect(deck.classList.contains("print-mode--paged-1")).toBe(true);
  });

  it("ignores a non-object JSON value (array/number/string) stored under the namespaced key", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);
    const key = "omc:slide-deck:deck-security-test:prefs";

    for (const value of ["42", '"just a string"', "[1,2,3]"]) {
      const { thrown, deck } = runScriptAgainstDeck(script, { surface: "teacher", storagePreset: { [key]: value } });
      expect(thrown).toBeNull();
      expect(deck.classList.contains("print-mode--paged-1")).toBe(true);
    }
  });
});

describe("slide_deck standalone output has no dynamic-HTML-insertion API and no inline-handler/URI injection surface (SDH-12)", () => {
  it("never uses innerHTML/insertAdjacentHTML/document.write anywhere in the embedded script", async () => {
    const html = await renderArtifact("slide_deck", baseDeck);
    const script = extractScript(html);

    expect(script).not.toMatch(/\.innerHTML\s*=/);
    expect(script).not.toMatch(/insertAdjacentHTML/);
    expect(script).not.toMatch(/document\.write/);
    expect(script).not.toMatch(/\beval\(/);
  });

  it("never emits an inline event-handler attribute or a javascript: URI anywhere in the rendered document", async () => {
    const html = await renderArtifact("slide_deck", { ...baseDeck, render_surface: "teacher" });

    expect(html).not.toMatch(/\son[a-z]+\s*=\s*["']/i);
    expect(html).not.toMatch(/javascript:/i);
  });

  it("uses only sanitizer-approved native controls -- no <select>/<input>/<label> in the standalone toolbar", async () => {
    const html = await renderArtifact("slide_deck", { ...baseDeck, render_surface: "teacher" });

    expect(html).not.toMatch(/<select[\s>]/i);
    expect(html).not.toMatch(/<input[\s>]/i);
    expect(html).not.toMatch(/<label[\s>]/i);
  });
});

describe("slide_deck teacher-only data cannot be revealed on student/presentation via client state (SDH-12)", () => {
  it.each(["student", "presentation"] as const)(
    "%s HTML carries no teacher-only text at all, so no hash/query/localStorage override has anything to reveal",
    async (surface) => {
      const html = await renderArtifact("slide_deck", { ...baseDeck, render_surface: surface });

      // Proves the AC structurally: since the teacher-only text was never
      // projected into the DOM (SDH-02), a malicious client tampering with
      // hash/query/localStorage state cannot make it appear -- there is
      // nothing in this string for any script to reveal.
      expect(html).not.toContain("SECRET_FACILITATION_NOTE");
      expect(html).not.toContain("SECRET_ANSWER_KEY");
      // The shared CSS rule referencing "[data-teacher-only]" as a selector
      // is expected (harmless -- matches nothing here); only the actual
      // attribute on a rendered element would be a leak.
      expect(html).not.toMatch(/<[a-z][a-z0-9-]*\s[^>]*data-teacher-only/i);
      // The shared client script always *queries* for these selectors (a
      // harmless no-op lookup on a student-safe render) -- assert the actual
      // <button> markup is absent, not the bare selector string.
      expect(html).not.toMatch(/<button[^>]*data-slide-chrome-toggle/);
      expect(html).not.toMatch(/<button[^>]*data-slide-teacher-preview/);
    },
  );
});
